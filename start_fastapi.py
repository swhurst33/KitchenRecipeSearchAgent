#!/usr/bin/env python3
"""
Startup script for FastAPI Recipe Discovery Agent
"""

import uvicorn
from agent_api import app

if __name__ == "__main__":
    print("Starting Kitchnsync Recipe Discovery Agent (FastAPI)")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )