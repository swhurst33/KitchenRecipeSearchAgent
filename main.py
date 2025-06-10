"""
WSGI/ASGI compatible application wrapper
"""
import asyncio
from typing import Any, Dict, List
from agent_api import app as fastapi_app

class ASGItoWSGI:
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app
    
    def __call__(self, environ: Dict[str, Any], start_response):
        # Create ASGI scope from WSGI environ
        scope = {
            "type": "http",
            "method": environ["REQUEST_METHOD"],
            "path": environ.get("PATH_INFO", "/"),
            "query_string": environ.get("QUERY_STRING", "").encode(),
            "headers": [
                (key.lower().replace("_", "-").encode(), value.encode())
                for key, value in environ.items()
                if key.startswith("HTTP_")
            ],
        }
        
        # Add content-type and content-length headers
        if "CONTENT_TYPE" in environ:
            scope["headers"].append((b"content-type", environ["CONTENT_TYPE"].encode()))
        if "CONTENT_LENGTH" in environ:
            scope["headers"].append((b"content-length", environ["CONTENT_LENGTH"].encode()))
        
        response = {"status": 500, "headers": [], "body": b""}
        
        async def receive():
            # Read request body if present
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                if content_length > 0:
                    body = environ['wsgi.input'].read(content_length)
                    return {"type": "http.request", "body": body}
                else:
                    return {"type": "http.request", "body": b""}
            except:
                return {"type": "http.request", "body": b""}
        
        async def send(message):
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response["body"] += message.get("body", b"")
        
        # Run the ASGI app
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.asgi_app(scope, receive, send))
        finally:
            loop.close()
        
        # Send WSGI response
        status_line = f"{response['status']} {self._get_status_text(response['status'])}"
        headers = [(header[0].decode(), header[1].decode()) for header in response["headers"]]
        
        start_response(status_line, headers)
        return [response["body"]]
    
    def _get_status_text(self, status_code: int) -> str:
        status_texts = {
            200: "OK",
            201: "Created", 
            400: "Bad Request",
            404: "Not Found",
            422: "Unprocessable Entity",
            500: "Internal Server Error"
        }
        return status_texts.get(status_code, "Unknown")

# Create WSGI-compatible app
app = ASGItoWSGI(fastapi_app)