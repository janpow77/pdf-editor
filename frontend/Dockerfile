FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

# Text-Assets einmalig maximal komprimieren; nginx liefert sie per
# gzip_static aus, statt bei jedem Abruf neu zu komprimieren.
RUN find dist -type f \( -name '*.js' -o -name '*.mjs' -o -name '*.css' \
        -o -name '*.html' -o -name '*.svg' -o -name '*.json' \) \
        -size +1k -exec gzip -9 -k {} \;

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
