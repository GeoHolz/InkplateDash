FROM python:3.11-slim

# Installer locales et police
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    fonts-dejavu-core \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libpangocairo-1.0-0 \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# Générer la locale française
RUN echo "fr_FR.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

# Définir les variables d’environnement pour la locale
ENV LANG=fr_FR.UTF-8 \
    LANGUAGE=fr_FR:fr \
    LC_ALL=fr_FR.UTF-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard.py .
COPY birthday.png .
COPY Ubuntu-R.ttf .
COPY entrypoint.sh .
COPY icons/ ./icons/

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]