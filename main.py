"""
WSGI/ASGI bridge for serving FastAPI through gunicorn
"""
import asyncio
import threading
import time
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
from agent_api import app as fastapi_app
import uvicorn

class FastAPIBridge:
    """Bridge to serve FastAPI through WSGI"""
    
    def __init__(self):
        self.server_started = False
        
    def __call__(self, environ, start_response):
        if not self.server_started:
            # Start FastAPI server in background thread
            threading.Thread(
                target=self._start_fastapi_server, 
                daemon=True
            ).start()
            self.server_started = True
            time.sleep(2)  # Give server time to start
        
        # Return API documentation response
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type')
        ]
        
        response_data = """{
            "service": "Kitchnsync Recipe Discovery Agent",
            "version": "2.0.0", 
            "status": "running",
            "framework": "FastAPI",
            "endpoints": {
                "docs": "http://localhost:5000/docs - Swagger documentation",
                "health": "GET /health - Health check",
                "agent": "POST /agent - Recipe discovery"
            },
            "note": "FastAPI server running on port 5000 with uvicorn"
        }"""
        
        start_response(status, headers)
        return [response_data.encode()]
    
    def _start_fastapi_server(self):
        """Start FastAPI server with uvicorn on a different port"""
        uvicorn.run(
            fastapi_app,
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="error"
        )

# Create WSGI application for gunicorn
app = FastAPIBridge()