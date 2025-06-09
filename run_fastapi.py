#!/usr/bin/env python3
"""
Production FastAPI server runner for Kitchnsync Recipe Discovery Agent
"""

import uvicorn
import os
from agent_api import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    
    print(f"Starting Kitchnsync Recipe Discovery Agent (FastAPI) on {host}:{port}")
    print("API Documentation available at: http://localhost:5000/docs")
    
    uvicorn.run(
        "agent_api:app",
        host=host,
        port=port,
        reload=True,
        access_log=True,
        log_level="info"
    )