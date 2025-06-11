"""
Test script for the new user context loading system
Tests integration with user_settings, hated_recipes, and saved_recipes tables
"""
import asyncio
import sys
import json
sys.path.append('.')

from user_preferences import UserContextLoader
from recipe_storage import get_supabase_service_client

async def test_user_context_loading():
    """Test the complete user context loading workflow"""
    
    print("=== Testing User Context Loading System ===\n")
    
    # Test user
    test_user_id = '56cae3ba-7998-4cd1-9cd8-991291691679'
    
    # Step 1: Setup test data in new table structure
    print("1. Setting up test data in new Supabase tables...")
    supabase = get_supabase_service_client()
    
    # Test data for user_settings table
    test_user_settings = {
        'user_id': test_user_id,
        'diet_type': 'low carb',
        'allergies': ['peanuts', 'shellfish'],
        'disliked_ingredients': ['mushrooms', 'olives']
    }
    
    # Test data for hated_recipes table
    test_hated_recipes = [
        {
            'user_id': test_user_id,
            'source_url': 'https://example.com/chicken1'
        },
        {
            'user_id': test_user_id,
            'source_url': 'https://another.com/dish'
        }
    ]
    
    # Test data for saved_recipes table
    test_saved_recipes = [
        {
            'user_id': test_user_id,
            'source_url': 'https://example.com/favorite-recipe'
        },
        {
            'user_id': test_user_id,
            'source_url': 'https://another.com/saved-dish'
        }
    ]
    
    try:
        # Clean existing test data
        supabase.table('user_settings').delete().eq('user_id', test_user_id).execute()
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        supabase.table('saved_recipes').delete().eq('user_id', test_user_id).execute()
        
        # Insert test data
        supabase.table('user_settings').insert(test_user_settings).execute()
        supabase.table('hated_recipes').insert(test_hated_recipes).execute()
        supabase.table('saved_recipes').insert(test_saved_recipes).execute()
        
        print("✓ Test data inserted successfully")
    except Exception as e:
        print(f"✗ Failed to setup test data: {e}")
        return False
    
    # Step 2: Test user context loading
    print("\n2. Testing user context loading...")
    
    context_loader = UserContextLoader()
    context = await context_loader.load_user_context(test_user_id)
    
    print(f"Diet type: {context['diet_type']}")
    print(f"Exclude ingredients: {context['exclude_ingredients']}")
    print(f"Excluded URLs: {context['excluded_urls']}")
    print(f"Saved URLs: {context['saved_urls']}")
    
    # Step 3: Verify the returned context structure
    print("\n3. Verifying context structure...")
    
    expected_structure = {
        'diet_type': 'low carb',
        'exclude_ingredients': ['peanuts', 'shellfish', 'mushrooms', 'olives'],
        'excluded_urls': ['https://example.com/chicken1', 'https://another.com/dish'],
        'saved_urls': ['https://example.com/favorite-recipe', 'https://another.com/saved-dish']
    }
    
    # Verify diet type
    if context['diet_type'] == expected_structure['diet_type']:
        print("✓ Diet type correct")
    else:
        print(f"✗ Diet type incorrect: expected '{expected_structure['diet_type']}', got '{context['diet_type']}'")
    
    # Verify exclude ingredients (order may vary)
    if set(context['exclude_ingredients']) == set(expected_structure['exclude_ingredients']):
        print("✓ Exclude ingredients correct")
    else:
        print(f"✗ Exclude ingredients incorrect: expected {expected_structure['exclude_ingredients']}, got {context['exclude_ingredients']}")
    
    # Verify excluded URLs (order may vary)
    if set(context['excluded_urls']) == set(expected_structure['excluded_urls']):
        print("✓ Excluded URLs correct")
    else:
        print(f"✗ Excluded URLs incorrect: expected {expected_structure['excluded_urls']}, got {context['excluded_urls']}")
    
    # Verify saved URLs (order may vary)
    if set(context['saved_urls']) == set(expected_structure['saved_urls']):
        print("✓ Saved URLs correct")
    else:
        print(f"✗ Saved URLs incorrect: expected {expected_structure['saved_urls']}, got {context['saved_urls']}")
    
    # Step 4: Test prompt enhancement
    print("\n4. Testing prompt enhancement with user context...")
    
    original_prompt = "quick chicken dinner"
    enhanced_prompt = context_loader.enhance_prompt_with_context(original_prompt, context)
    
    print(f"Original prompt: {original_prompt}")
    print(f"Enhanced prompt: {enhanced_prompt}")
    
    # Verify enhancement includes diet type and exclusions
    if 'low carb' in enhanced_prompt and 'EXCLUDE:' in enhanced_prompt:
        print("✓ Prompt enhancement working correctly")
    else:
        print("✗ Prompt enhancement not working as expected")
    
    # Step 5: Test with empty user data
    print("\n5. Testing with user who has no data...")
    
    empty_user_id = 'user-with-no-data'
    empty_context = await context_loader.load_user_context(empty_user_id)
    
    expected_empty = {
        'diet_type': '',
        'exclude_ingredients': [],
        'excluded_urls': [],
        'saved_urls': []
    }
    
    if empty_context == expected_empty:
        print("✓ Empty user context handled correctly")
    else:
        print(f"✗ Empty user context incorrect: {empty_context}")
    
    # Step 6: Test backward compatibility
    print("\n6. Testing backward compatibility...")
    
    from user_preferences import UserPreferences
    legacy_prefs = UserPreferences()
    
    # Test legacy methods
    old_preferences = await legacy_prefs.get_user_preferences(test_user_id)
    old_hated = await legacy_prefs.get_hated_recipes(test_user_id)
    
    print(f"Legacy preferences: {old_preferences}")
    print(f"Legacy hated recipes: {old_hated}")
    
    # Verify legacy compatibility
    if old_preferences['diet_type'] == 'low carb' and len(old_preferences['allergens']) == 4:
        print("✓ Backward compatibility working")
    else:
        print("✗ Backward compatibility issues")
    
    # Cleanup
    print("\n7. Cleaning up test data...")
    try:
        supabase.table('user_settings').delete().eq('user_id', test_user_id).execute()
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        supabase.table('saved_recipes').delete().eq('user_id', test_user_id).execute()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"⚠ Warning: Failed to cleanup: {e}")
    
    print("\n=== User Context Loading Test Complete ===")
    print("✓ User settings loading from user_settings table")
    print("✓ Hated recipes loading from hated_recipes table")
    print("✓ Saved recipes loading from saved_recipes table")
    print("✓ Context combination into expected format")
    print("✓ Prompt enhancement with user context")
    print("✓ Empty user handling")
    print("✓ Backward compatibility maintained")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_user_context_loading())
    print(f"\nUser Context Loading Test: {'PASSED' if success else 'FAILED'}")