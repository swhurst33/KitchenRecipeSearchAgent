#!/usr/bin/env python3
"""
Test script for POST /agent endpoint
"""

import requests
import json

def test_agent_endpoint():
    """Test the POST /agent endpoint with curl command examples"""
    
    url = 'https://kitchen-recipe-agent-swhurst33.replit.app/agent'
    headers = {'Content-Type': 'application/json'}
    data = {
        'prompt': 'quick keto dinner',
        'user_id': 'test-123'
    }
    
    print("=== Testing POST /agent Endpoint ===\n")
    
    # Show curl command
    print("1. CURL Command for Replit Shell:")
    print("```bash")
    print(f"curl -X POST {url} \\")
    print("  -H \"Content-Type: application/json\" \\")
    print("  -d '{")
    print(f'    "prompt": "{data["prompt"]}",')
    print(f'    "user_id": "{data["user_id"]}"')
    print("  }' \\")
    print("  --max-time 45")
    print("```\n")
    
    # Show Postman setup
    print("2. POSTMAN Setup:")
    print("   Method: POST")
    print(f"   URL: {url}")
    print("   Headers:")
    print("     Content-Type: application/json")
    print("   Body Type: raw (JSON)")
    print("   Body Content:")
    print(json.dumps(data, indent=4))
    print()
    
    # Test the endpoint
    print("3. Testing the endpoint...")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=45)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: ~{response.elapsed.total_seconds():.2f} seconds")
        
        if response.status_code == 200:
            print("\n✓ SUCCESS - Endpoint is working!")
            print("\nResponse JSON:")
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
            
            # Show summary
            if 'recipes' in response_data:
                recipes = response_data['recipes']
                print(f"\n📋 Summary: Found {len(recipes)} recipes")
                for i, recipe in enumerate(recipes[:3], 1):
                    print(f"  {i}. {recipe.get('title', 'Unknown')}")
                    if recipe.get('image_url'):
                        print(f"     Image: {recipe['image_url'][:60]}...")
                    
        else:
            print(f"\n❌ ERROR - Status {response.status_code}")
            print("Response:")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("❌ ERROR - Request timed out (45 seconds)")
    except requests.exceptions.ConnectionError:
        print("❌ ERROR - Could not connect to server")
    except Exception as e:
        print(f"❌ ERROR - {e}")

if __name__ == "__main__":
    test_agent_endpoint()