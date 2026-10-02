FROM python:3.13-slim

# Skip writing .pyc files, and send logs straight to `docker compose logs` without buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer stays cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the API goes in the image. The terminal game (main.py, pygame audio,
# sounds/) runs on the host.
COPY app.py database.py ./

RUN useradd --create-home appuser
USER appuser

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
