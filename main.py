# Import the FastAPI app for ASGI compatibility
from agent import app

# This file exposes the FastAPI app for the ASGI server
# The app can be run with: uvicorn main:app --host 0.0.0.0 --port 5000 --reload
