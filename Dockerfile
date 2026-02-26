# Trolley Problem Arena — deploy from source (Cloud Run, Railway, etc.)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files and app live under app/
ENV PYTHONPATH=/app
EXPOSE 8000

# Cloud Run / Railway set PORT; default 8000
ENV PORT=8000
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
