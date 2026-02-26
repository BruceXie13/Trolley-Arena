# Trolley Problem Arena — deploy from source (Cloud Run, Railway, etc.)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files and app live under app/
ENV PYTHONPATH=/app
EXPOSE 8000

# Use a script so PORT is always expanded (some platforms run CMD without a shell)
ENV PORT=8000
RUN chmod +x start.sh
CMD ["./start.sh"]
