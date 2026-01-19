import argparse
import os

import uvicorn


def run_api() -> None:
    parser = argparse.ArgumentParser(description="Run CRM Analytics API")
    parser.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")))
    args = parser.parse_args()
    uvicorn.run("backend.main:app", host=args.host, port=args.port)
