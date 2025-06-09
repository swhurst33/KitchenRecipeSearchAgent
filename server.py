#!/usr/bin/env python3
"""
Production FastAPI server for Kitchnsync Recipe Discovery Agent
"""

import uvicorn
import os
import sys
from agent_api import app

def main():
    """Start the FastAPI server with production settings"""
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    
    print(f"Starting Kitchnsync Recipe Discovery Agent on {host}:{port}")
    print("✓ FastAPI framework with CORS enabled")
    print("✓ Swagger documentation at /docs")
    print("✓ Recipe discovery endpoint at POST /agent")
    print("✓ Health check at GET /health")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        print(f"Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()