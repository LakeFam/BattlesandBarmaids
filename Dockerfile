FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API and the game rules it plays; the terminal client runs on the host.
COPY app.py database.py migrate.py runs.py entities.py combat.py data.py ./
COPY migrations/ migrations/

RUN useradd --create-home appuser
USER appuser

EXPOSE 5000
# Apply new migrations, then serve.
CMD ["sh", "-c", "python migrate.py && exec gunicorn --bind 0.0.0.0:5000 --workers 2 app:app"]
