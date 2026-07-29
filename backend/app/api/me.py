"""Konto-Selbstverwaltung: Werkzeug-Einstellungen und Selbstlöschung (Art. 17 DSGVO)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas_auth import AccountDelete
from app.security import verify_password

router = APIRouter(prefix="/me", tags=["Konto"])


@router.get("/preferences")
def get_preferences(user: User = Depends(get_current_user)):
    return user.preferences or {}


@router.put("/preferences")
def put_preferences(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Freies JSON-Objekt mit Werkzeug-Voreinstellungen (Größe begrenzt)."""
    size = len(json.dumps(payload, ensure_ascii=False).encode())
    if size > settings.preferences_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Einstellungen zu groß (max {settings.preferences_max_bytes // 1024} KB)",
        )
    db_user = db.get(User, user.id)
    db_user.preferences = payload
    db.commit()
    return db_user.preferences


@router.delete("", status_code=204)
def delete_account(
    payload: AccountDelete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Konto endgültig löschen (Passwort-Bestätigung erforderlich)."""
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Passwort ist falsch")
    db_user = db.get(User, user.id)
    db.delete(db_user)
    db.commit()
    return Response(status_code=204)
