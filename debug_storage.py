#!/usr/bin/env python3
import asyncio
import sys
import uuid
sys.path.append('.')
from recipe_storage import store_searched_recipe

async def test_direct_storage():
    """Test storing a recipe directly to debug the issue"""
    
    test_uuid = str(uuid.uuid4())
    print(f"Testing direct storage with UUID: {test_uuid}")
    
    # Test recipe data
    test_recipe = {
        'title': 'Test Recipe for Storage',
        'image_url': 'https://example.com/image.jpg',
        'description': 'A test recipe to verify storage functionality',
        'ingredients': [
            {'text': '1 cup flour', 'quantity': 1.0, 'unit': 'cup'},
            {'text': '2 eggs', 'quantity': 2.0, 'unit': 'pieces'}
        ],
        'instructions': [
            'Mix flour and eggs',
            'Cook until done'
        ],
        'source_url': 'https://example.com/recipe'
    }
    
    try:
        await store_searched_recipe(test_recipe, test_uuid)
        print("✓ Direct storage test completed")
        
        # Verify it was stored
        from supabase_sources import get_supabase_client
        supabase = get_supabase_client()
        response = supabase.table('recipe_search').select('*').eq('user_id', test_uuid).execute()
        
        if response.data:
            print(f"✓ Found {len(response.data)} stored recipes")
            for recipe in response.data:
                print(f"  - {recipe.get('title', 'Unknown')}")
        else:
            print("✗ No recipes found after storage")
            
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_storage())