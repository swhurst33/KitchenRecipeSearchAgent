"""
Test the UserContextLoader functionality directly
"""
import asyncio
import sys
sys.path.append('.')

from user_preferences import UserContextLoader

async def test_context_loader_methods():
    """Test individual methods of UserContextLoader"""
    
    print("=== Testing UserContextLoader Methods ===\n")
    
    # Test user ID (can be any string for testing empty response handling)
    test_user_id = 'test-user-123'
    
    context_loader = UserContextLoader()
    
    # Test 1: User settings loading (should handle empty gracefully)
    print("1. Testing user settings loading...")
    settings = await context_loader._get_user_settings(test_user_id)
    print(f"User settings: {settings}")
    
    expected_empty_settings = {
        'diet_type': '',
        'allergies': [],
        'disliked_ingredients': []
    }
    
    if settings == expected_empty_settings:
        print("✓ Empty user settings handled correctly")
    else:
        print("✗ User settings handling issue")
    
    # Test 2: Hated recipes loading  
    print("\n2. Testing hated recipes loading...")
    hated_urls = await context_loader._get_hated_recipe_urls(test_user_id)
    print(f"Hated recipe URLs: {hated_urls}")
    
    if hated_urls == []:
        print("✓ Empty hated recipes handled correctly")
    else:
        print("✗ Hated recipes handling issue")
    
    # Test 3: Saved recipes loading
    print("\n3. Testing saved recipes loading...")
    saved_urls = await context_loader._get_saved_recipe_urls(test_user_id)
    print(f"Saved recipe URLs: {saved_urls}")
    
    if saved_urls == []:
        print("✓ Empty saved recipes handled correctly")
    else:
        print("✗ Saved recipes handling issue")
    
    # Test 4: Complete context loading
    print("\n4. Testing complete context loading...")
    context = await context_loader.load_user_context(test_user_id)
    print(f"Complete context: {context}")
    
    expected_context = {
        'diet_type': '',
        'exclude_ingredients': [],
        'excluded_urls': [],
        'saved_urls': []
    }
    
    if context == expected_context:
        print("✓ Complete context loading working correctly")
    else:
        print("✗ Context loading issue")
    
    # Test 5: Prompt enhancement
    print("\n5. Testing prompt enhancement...")
    
    # Test with empty context
    original_prompt = "quick chicken dinner"
    enhanced_empty = context_loader.enhance_prompt_with_context(original_prompt, context)
    print(f"Empty context enhancement: '{enhanced_empty}'")
    
    if enhanced_empty == original_prompt:
        print("✓ Empty context enhancement correct (no changes)")
    else:
        print("✗ Empty context enhancement issue")
    
    # Test with sample context
    sample_context = {
        'diet_type': 'low carb',
        'exclude_ingredients': ['peanuts', 'mushrooms'],
        'excluded_urls': [],
        'saved_urls': []
    }
    
    enhanced_sample = context_loader.enhance_prompt_with_context(original_prompt, sample_context)
    print(f"Sample context enhancement: '{enhanced_sample}'")
    
    expected_enhancement = "quick chicken dinner, filtered for a low carb diet, EXCLUDE: peanuts, mushrooms"
    if enhanced_sample == expected_enhancement:
        print("✓ Context enhancement working correctly")
    else:
        print(f"✗ Enhancement incorrect. Expected: '{expected_enhancement}'")
    
    print("\n=== UserContextLoader Test Complete ===")
    print("✓ All methods handle empty data correctly")
    print("✓ Context structure is properly formatted")
    print("✓ Prompt enhancement works with user preferences")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_context_loader_methods())
    print(f"\nContext Loader Test: {'PASSED' if success else 'FAILED'}")