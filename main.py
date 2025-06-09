# WSGI wrapper for FastAPI to work with gunicorn
from agent_api import app as fastapi_app
import asyncio
from threading import Thread
import uvicorn

class ASGITransport:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Simple WSGI wrapper that starts uvicorn server
        if not hasattr(self, '_server_started'):
            Thread(target=self._start_uvicorn, daemon=True).start()
            self._server_started = True
        
        # Return a simple redirect to the uvicorn server
        status = '302 Found'
        headers = [('Location', f'http://{environ["HTTP_HOST"]}/')]
        start_response(status, headers)
        return [b'']
    
    def _start_uvicorn(self):
        uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info")

# Create WSGI app for gunicorn
app = ASGITransport(fastapi_app)