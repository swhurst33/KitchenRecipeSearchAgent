#!/usr/bin/env python3
"""
Test script for the Kitchnsync Recipe Discovery Agent API
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test the health endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(f"✓ Health check passed: {response.json()}")
    else:
        print(f"✗ Health check failed: {response.status_code}")

def test_recipe_agent(prompt, user_id="test_user"):
    """Test the recipe discovery agent"""
    print(f"\nTesting recipe discovery for: '{prompt}'")
    
    payload = {
        "prompt": prompt,
        "user_id": user_id
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/agent",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=45
    )
    end_time = time.time()
    
    print(f"Response time: {end_time - start_time:.2f} seconds")
    
    if response.status_code == 200:
        data = response.json()
        recipes = data.get('recipes', [])
        print(f"✓ Found {len(recipes)} recipes")
        
        # Show first recipe details
        if recipes:
            recipe = recipes[0]
            print(f"  Sample recipe: {recipe.get('title', 'Unknown')}")
            print(f"  Description: {recipe.get('description', 'N/A')[:100]}...")
            print(f"  Image URL: {recipe.get('image_url', 'N/A')}")
            print(f"  Recipe ID: {recipe.get('recipe_id', 'N/A')}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  Error: {response.text}")

def main():
    """Run API tests"""
    print("Kitchnsync Recipe Discovery Agent - API Test")
    print("=" * 50)
    
    # Test health check
    test_health_check()
    
    # Test various recipe prompts
    test_prompts = [
        "quick keto dinner",
        "healthy breakfast",
        "easy vegetarian lunch",
        "chocolate dessert"
    ]
    
    for prompt in test_prompts:
        test_recipe_agent(prompt)
        time.sleep(2)  # Brief pause between requests
    
    print(f"\nAPI testing complete!")
    print(f"Backend service is running at {BASE_URL}")

if __name__ == "__main__":
    main()