# No npm in Docker — corporate networks often block registry.npmjs.org (403).
# UI is pre-built in frontend/dist/ (see scripts/build-frontend.ps1).
FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY sample_data/ ./sample_data/
COPY frontend/dist/ ./frontend/dist/

WORKDIR /app/backend
ENV DJANGO_SETTINGS_MODULE=config.settings

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["sh", "/docker-entrypoint.sh"]
