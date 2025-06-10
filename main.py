"""
ASGI application for gunicorn with uvicorn workers
"""
from agent_api import app

# For ASGI compatibility with gunicorn
application = app