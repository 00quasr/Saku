# Saku im Netz, z. B. auf Railway: python -m saku server, Daten auf dem Volume /data (Anleitung: docs/DEPLOY.md)
FROM python:3.12-slim

# curl: python -m saku assets lädt Basecoat, htmx, Icons und Schriften, die nicht im Repo liegen
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# ohne pywebview (App-Fenster) und fastembed (Vektormodell, 240 MB und mehrere hundert MB Arbeitsspeicher): die Suche
# nach Bedeutung fällt auf die Volltextsuche zurück. fonttools und brotli reduzieren beim Bauen die japanische Schrift.
RUN grep -v -E "^(pywebview|fastembed)" requirements.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt fonttools brotli

COPY . .
RUN python -m saku assets

ENV SAKU_DATENORDNER=/data PYTHONUNBUFFERED=1
CMD ["python", "-m", "saku", "server"]
