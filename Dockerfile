# Trolley Problem Arena — deploy from source (Cloud Run, Railway, etc.)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files and app live under app/
ENV PYTHONPATH=/app
EXPOSE 8000

# No shell or port arg: Python reads PORT from env (works when platform overrides CMD)
ENV PORT=8000
CMD ["python", "run.py"]
