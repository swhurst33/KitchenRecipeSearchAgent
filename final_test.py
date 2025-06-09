#!/usr/bin/env python3
import requests
import json
import asyncio
import sys
sys.path.append('.')
from recipe_storage import get_supabase_service_client

def final_test():
    """Complete test of recipe discovery and storage"""
    
    existing_user_id = '56cae3ba-7998-4cd1-9cd8-991291691679'
    
    # Clear previous test recipes first
    print("Clearing previous test recipes...")
    try:
        supabase = get_supabase_service_client()
        supabase.table('recipe_search').delete().eq('user_id', existing_user_id).execute()
        print("Previous recipes cleared")
    except Exception as e:
        print(f"Could not clear previous recipes: {e}")
    
    print("\nSending recipe request to agent...")
    response = requests.post(
        'https://kitchen-recipe-agent-swhurst33.replit.app/agent',
        headers={'Content-Type': 'application/json'},
        json={'prompt': 'chicken curry recipe', 'user_id': existing_user_id},
        timeout=60
    )
    
    print(f"API Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"API returned {len(data.get('recipes', []))} recipes")
        
        # Wait a moment for async storage to complete
        import time
        time.sleep(3)
        
        # Check what was actually stored
        try:
            response = supabase.table('recipe_search').select('*').eq('user_id', existing_user_id).execute()
            
            if response.data:
                print(f"\nSuccessfully stored {len(response.data)} recipes:")
                for recipe in response.data:
                    print(f"- {recipe.get('title', 'Unknown')}")
                    print(f"  Ingredients: {len(recipe.get('ingredients', []))}")
                    print(f"  Instructions: {len(recipe.get('instructions', []))}")
                    print(f"  Source: {recipe.get('source_url', 'Unknown')}")
                    print()
                
                return True
            else:
                print("\nNo recipes were stored in the database")
                return False
                
        except Exception as e:
            print(f"Error checking stored recipes: {e}")
            return False
    else:
        print(f"API Error: {response.text}")
        return False

if __name__ == "__main__":
    success = final_test()
    
    print("\n" + "="*50)
    if success:
        print("SUCCESS: Recipe storage integration is working")
        print("Recipes are being saved to your recipe_search table")
    else:
        print("ISSUE: Recipe storage needs debugging")
        print("Check server logs for storage error messages")