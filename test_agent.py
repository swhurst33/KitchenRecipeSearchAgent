#!/usr/bin/env python3
"""
Test script for the Kitchnsync Recipe Discovery Agent
Tests all endpoints and functionality
"""

import json
import requests
import time
import threading
import uvicorn
from agent import app

def start_server():
    """Start the FastAPI server in a separate thread"""
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="error")

def test_agent():
    """Test all agent endpoints"""
    print("🚀 Starting Kitchnsync Recipe Discovery Agent test...")
    
    # Start server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Health check endpoint
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health check passed: {result['message']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: Intent extraction endpoint
    print("\n2. Testing intent extraction...")
    try:
        test_prompt = "quick keto dinner"
        response = requests.post(
            f"{base_url}/extract-intent",
            json={"prompt": test_prompt},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            intent = response.json()
            print(f"✅ Intent extraction successful:")
            print(f"   Meal type: {intent.get('meal_type')}")
            print(f"   Diet type: {intent.get('diet_type')}")
            print(f"   Keywords: {intent.get('keywords')}")
            print(f"   Search queries: {intent.get('search_queries')}")
        else:
            print(f"❌ Intent extraction failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Intent extraction error: {e}")
    
    # Test 3: Recipe agent endpoint (main functionality)
    print("\n3. Testing recipe discovery agent...")
    try:
        test_prompts = [
            "easy vegetarian pasta",
            "quick chicken dinner",
            "healthy breakfast"
        ]
        
        for prompt in test_prompts:
            print(f"\n   Testing prompt: '{prompt}'")
            response = requests.post(
                f"{base_url}/agent",
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"},
                timeout=30  # Allow time for recipe parsing
            )
            
            if response.status_code == 200:
                result = response.json()
                recipes = result.get('recipes', [])
                print(f"   ✅ Found {len(recipes)} recipes")
                
                if recipes:
                    # Show details of first recipe
                    recipe = recipes[0]
                    print(f"   📖 Sample recipe: {recipe.get('title', 'Unknown')}")
                    print(f"   🔗 Source: {recipe.get('source_url', 'N/A')}")
                    print(f"   🥘 Ingredients: {len(recipe.get('ingredients', []))}")
                    print(f"   📋 Instructions: {len(recipe.get('instructions', []))}")
                    if recipe.get('macros'):
                        macros = recipe['macros']
                        print(f"   📊 Macros: {macros.get('calories', 'N/A')} cal, {macros.get('protein', 'N/A')}g protein")
                else:
                    print(f"   ⚠️  No recipes found for '{prompt}'")
            else:
                print(f"   ❌ Recipe search failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
    except Exception as e:
        print(f"❌ Recipe agent error: {e}")
    
    print("\n🏁 Testing complete!")
    
    # Keep server running for manual testing
    print("\n💡 Server is running at http://localhost:5000")
    print("   - Health check: GET /")
    print("   - Extract intent: POST /extract-intent")
    print("   - Recipe discovery: POST /agent")
    print("\nPress Ctrl+C to stop the server...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == "__main__":
    test_agent()