#!/usr/bin/env python3
import requests
import json
import uuid
import asyncio
import sys
sys.path.append('.')
from supabase_sources import get_supabase_client

def test_recipe_storage():
    """Test the complete recipe storage workflow"""
    
    # Generate a proper UUID for testing
    test_uuid = str(uuid.uuid4())
    print(f"Testing with UUID: {test_uuid}")
    
    print("\n1. Sending recipe request to API...")
    try:
        response = requests.post(
            'https://kitchen-recipe-agent-swhurst33.replit.app/agent',
            headers={'Content-Type': 'application/json'},
            json={'prompt': 'healthy breakfast smoothie', 'user_id': test_uuid},
            timeout=45
        )
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recipe_count = len(data.get('recipes', []))
            print(f"API returned {recipe_count} recipes")
            
            # Show first recipe for verification
            if recipe_count > 0:
                first_recipe = data['recipes'][0]
                print(f"First recipe: {first_recipe.get('title', 'Unknown')}")
        else:
            print(f"API Error: {response.text}")
            return
            
    except Exception as e:
        print(f"Request failed: {e}")
        return
    
    print("\n2. Checking Supabase recipe_search table...")
    
    async def check_stored_recipes():
        try:
            supabase = get_supabase_client()
            
            # Query the recipe_search table for our test user
            response = supabase.table('recipe_search').select('*').eq('user_id', test_uuid).execute()
            
            if response.data:
                print(f"✓ Found {len(response.data)} stored recipes in recipe_search table:")
                for i, recipe in enumerate(response.data, 1):
                    print(f"  {i}. {recipe.get('title', 'Unknown')}")
                    print(f"     - Source: {recipe.get('source_url', 'Unknown')}")
                    print(f"     - Ingredients: {len(recipe.get('ingredients', []))} items")
                    print(f"     - Instructions: {len(recipe.get('instructions', []))} steps")
                    print(f"     - Created: {recipe.get('created_at', 'Unknown')}")
                    print()
                return True
            else:
                print("✗ No recipes found in recipe_search table")
                return False
                
        except Exception as e:
            print(f"✗ Error checking stored recipes: {e}")
            return False
    
    # Run the async check
    stored = asyncio.run(check_stored_recipes())
    
    if stored:
        print("✓ Recipe storage integration is working correctly!")
    else:
        print("✗ Recipe storage integration needs debugging")

if __name__ == "__main__":
    test_recipe_storage()