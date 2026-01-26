#!/bin/sh
set -e

if [ "${GENERATE_SAMPLE_DATA:-1}" = "1" ]; then
  python /app/scripts/generate_sample_data.py
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
