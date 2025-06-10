"""
Direct FastAPI server runner using uvicorn for proper ASGI support
"""
import uvicorn
from agent_api import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )