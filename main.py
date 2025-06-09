# Import FastAPI app for gunicorn compatibility using uvicorn workers
from agent_api import app

# This allows gunicorn to serve FastAPI using: gunicorn -k uvicorn.workers.UvicornWorker main:app