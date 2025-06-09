"""
ASGI configuration for FastAPI Recipe Discovery Agent
Compatible with gunicorn using uvicorn workers
"""

from agent_api import app

# ASGI application for gunicorn with uvicorn workers
# Run with: gunicorn -k uvicorn.workers.UvicornWorker asgi:app
application = app