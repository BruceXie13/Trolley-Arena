#!/bin/sh
# So PORT is always expanded (platforms often run CMD without a shell)
port=${PORT:-8000}
exec uvicorn app.main:app --host 0.0.0.0 --port "$port"
