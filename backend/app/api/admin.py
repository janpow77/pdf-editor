"""Admin-Bereich: Nutzerverwaltung und Konfigurations-Übersicht.

Bewusst schlank (kein Port des verflochtenen audit_designer-Admin-Routers).
Schutzregeln: Admins können weder sich selbst noch den letzten aktiven Admin
deaktivieren oder löschen.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.config import settings
from app.db import get_db
from app.models import User, UserRole
from app.schemas_auth import AdminUserResponse, AdminUserUpdate, ToolAccessUpdate
from app.tool_access import get_login_required_tools, set_login_required_tools
from app.tool_catalog import TOOL_CATALOG, TOOL_IDS

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


def _to_response(user: User) -> AdminUserResponse:
    resp = AdminUserResponse.model_validate(user)
    resp.locked = user.is_locked
    return resp


def _guard_admin_integrity(target: User, actor: User, db: Session, action: str) -> None:
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail=f"Sie können sich nicht selbst {action}")
    if target.role == UserRole.ADMIN:
        other_admins = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != target.id)
            .count()
        )
        if other_admins == 0:
            raise HTTPException(
                status_code=400, detail="Der letzte aktive Administrator kann nicht entfernt werden"
            )


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    users = (
        db.query(User).order_by(User.id).offset(offset).limit(min(limit, 200)).all()
    )
    return [_to_response(u) for u in users]


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    if not payload.is_active:
        _guard_admin_integrity(user, actor, db, "deaktivieren")
    user.is_active = payload.is_active
    db.commit()
    return _to_response(user)


@router.post("/users/{user_id}/unlock", response_model=AdminUserResponse)
def unlock_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    user.locked_until = None
    user.failed_login_attempts = 0
    db.commit()
    return _to_response(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    _guard_admin_integrity(user, actor, db, "löschen")
    db.delete(user)
    db.commit()


@router.get("/config")
def get_config():
    """Nicht-geheime Laufzeit-Konfiguration."""
    return {
        "max_file_size_mb": settings.max_file_size_mb,
        "max_total_size_mb": settings.max_total_size_mb,
        "max_file_size_mb_authed": settings.max_file_size_mb_authed,
        "max_total_size_mb_authed": settings.max_total_size_mb_authed,
        "rate_limit_default": settings.rate_limit_default,
        "rate_limit_authed": settings.rate_limit_authed,
        "rate_limit_mail": settings.rate_limit_mail,
        "mail_configured": bool(settings.smtp_host),
        "mail_max_attachment_mb": settings.mail_max_attachment_mb,
        "preferences_max_bytes": settings.preferences_max_bytes,
    }


# ── Werkzeug-Freigabe ─────────────────────────────────────────


@router.get("/tool-access")
def get_tool_access():
    """Alle Werkzeuge mit dem Kennzeichen, ob sie eine Anmeldung verlangen."""
    restricted = get_login_required_tools(force=True)
    return {
        "tools": [
            {
                "id": t.id,
                "label": t.label,
                "group": t.group,
                "login_required": t.id in restricted,
            }
            for t in TOOL_CATALOG
        ],
        "login_required": sorted(restricted),
    }


@router.put("/tool-access")
def update_tool_access(payload: ToolAccessUpdate):
    """Liste der Werkzeuge setzen, die eine Anmeldung verlangen.

    Unbekannte IDs werden verworfen; eine leere Liste hebt alle Sperren auf.
    """
    unknown = sorted(set(payload.login_required) - TOOL_IDS)
    saved = set_login_required_tools(payload.login_required)
    return {"login_required": sorted(saved), "ignored": unknown}
