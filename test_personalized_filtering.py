"""
Test script for personalized recipe filtering system
Tests user preferences, hated recipes exclusion, and prompt enhancement
"""
import asyncio
import sys
import json
sys.path.append('.')

from user_preferences import UserPreferences
from recipe_filters import RecipeFilters
from recipe_storage import get_supabase_service_client

async def test_personalized_filtering():
    """Test the complete personalized filtering workflow"""
    
    # Use existing test user
    test_user_id = '56cae3ba-7998-4cd1-9cd8-991291691679'
    
    print("=== Testing Personalized Recipe Filtering ===\n")
    
    # Test 1: Create sample user preferences
    print("1. Setting up test user preferences...")
    supabase = get_supabase_service_client()
    
    # Insert test preferences (will overwrite if exists)
    test_preferences = {
        'user_id': test_user_id,
        'diet_type': 'vegan',
        'allergies': ['peanuts', 'shellfish'],
        'disliked_ingredients': ['cilantro', 'olives']
    }
    
    try:
        # Delete existing preferences first
        supabase.table('user_preferences').delete().eq('user_id', test_user_id).execute()
        
        # Insert new test preferences
        response = supabase.table('user_preferences').insert(test_preferences).execute()
        print(f"✓ Created test preferences for user {test_user_id}")
    except Exception as e:
        print(f"✗ Failed to create preferences: {e}")
        return False
    
    # Test 2: Create sample hated recipes
    print("\n2. Setting up test hated recipes...")
    
    test_hated_recipes = [
        {
            'user_id': test_user_id,
            'source_url': 'https://www.allrecipes.com/recipe/231506/simple-macaroni-and-cheese/'
        },
        {
            'user_id': test_user_id,
            'source_url': 'https://www.example.com/bad-recipe'
        }
    ]
    
    try:
        # Delete existing hated recipes first
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        
        # Insert new test hated recipes
        response = supabase.table('hated_recipes').insert(test_hated_recipes).execute()
        print(f"✓ Created {len(test_hated_recipes)} test hated recipes")
    except Exception as e:
        print(f"✗ Failed to create hated recipes: {e}")
        return False
    
    # Test 3: Test user preferences fetching
    print("\n3. Testing user preferences retrieval...")
    
    user_prefs = UserPreferences()
    preferences = await user_prefs.get_user_preferences(test_user_id)
    
    print(f"Diet type: {preferences['diet_type']}")
    print(f"Allergens: {preferences['allergens']}")
    print(f"Disliked ingredients: {preferences['disliked_ingredients']}")
    
    # Test 4: Test prompt enhancement
    print("\n4. Testing prompt enhancement...")
    
    original_prompt = "quick chicken dinner"
    enhanced_prompt = user_prefs.enhance_prompt_with_preferences(original_prompt, preferences)
    
    print(f"Original: {original_prompt}")
    print(f"Enhanced: {enhanced_prompt}")
    
    # Test 5: Test hated recipes filtering
    print("\n5. Testing hated recipes filtering...")
    
    recipe_filters = RecipeFilters()
    hated_urls = await user_prefs.get_hated_recipes(test_user_id)
    print(f"Found {len(hated_urls)} hated recipe URLs")
    
    # Test URL filtering
    test_urls = [
        'https://www.allrecipes.com/recipe/231506/simple-macaroni-and-cheese/',  # Should be filtered
        'https://www.example.com/good-recipe',  # Should pass
        'https://www.example.com/bad-recipe',  # Should be filtered
        'https://www.bbc.co.uk/food/recipes/good_recipe'  # Should pass
    ]
    
    filtered_urls = await recipe_filters.filter_recipe_urls(test_urls, test_user_id)
    print(f"Original URLs: {len(test_urls)}")
    print(f"Filtered URLs: {len(filtered_urls)}")
    print(f"Excluded URLs: {len(test_urls) - len(filtered_urls)}")
    
    # Show which URLs were kept
    print("Kept URLs:")
    for url in filtered_urls:
        print(f"  - {url}")
    
    print("\n=== Personalized Filtering Test Complete ===")
    
    # Cleanup - remove test data
    print("\n6. Cleaning up test data...")
    try:
        supabase.table('user_preferences').delete().eq('user_id', test_user_id).execute()
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"⚠ Warning: Failed to cleanup test data: {e}")
    
    return True

# Run the test
if __name__ == "__main__":
    success = asyncio.run(test_personalized_filtering())
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")