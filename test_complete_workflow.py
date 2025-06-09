#!/usr/bin/env python3
import requests
import json
import asyncio
import sys
sys.path.append('.')
from recipe_storage import get_supabase_service_client

def test_complete_workflow():
    """Test the complete recipe discovery and storage workflow"""
    
    # Use existing user from your database
    existing_user_id = '56cae3ba-7998-4cd1-9cd8-991291691679'
    
    print("Step 1: Sending recipe request to agent...")
    try:
        response = requests.post(
            'https://kitchen-recipe-agent-swhurst33.replit.app/agent',
            headers={'Content-Type': 'application/json'},
            json={'prompt': 'healthy dinner recipes', 'user_id': existing_user_id},
            timeout=60
        )
        
        print(f"API Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recipe_count = len(data.get('recipes', []))
            print(f"Returned {recipe_count} recipes:")
            
            for i, recipe in enumerate(data.get('recipes', [])[:3], 1):
                print(f"  {i}. {recipe.get('title', 'Unknown')}")
        else:
            print(f"API Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Request failed: {e}")
        return False
    
    print("\nStep 2: Verifying recipes stored in Supabase...")
    
    try:
        supabase = get_supabase_service_client()
        
        # Get recipes for this user from recipe_search table
        response = supabase.table('recipe_search').select('*').eq('user_id', existing_user_id).order('created_at', desc=True).limit(10).execute()
        
        if response.data:
            print(f"Found {len(response.data)} stored recipes in recipe_search table:")
            
            for i, recipe in enumerate(response.data[:5], 1):
                print(f"  {i}. {recipe.get('title', 'Unknown')}")
                print(f"     Source: {recipe.get('source_url', 'Unknown')}")
                print(f"     Ingredients: {len(recipe.get('ingredients', []))} items")
                print(f"     Instructions: {len(recipe.get('instructions', []))} steps")
                print(f"     Created: {recipe.get('created_at', 'Unknown')}")
                print()
            
            return True
        else:
            print("No recipes found in recipe_search table")
            return False
            
    except Exception as e:
        print(f"Database verification failed: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_workflow()
    
    if success:
        print("✓ Complete recipe storage workflow is working correctly!")
        print("✓ Recipes are being stored in your Supabase recipe_search table")
        print("✓ You can now queue recipes from the frontend")
    else:
        print("✗ Workflow test failed - check the logs above")