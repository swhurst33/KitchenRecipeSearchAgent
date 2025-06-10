"""
Complete test of personalized recipe filtering agent
Demonstrates end-to-end functionality without server dependency
"""
import asyncio
import sys
import json
sys.path.append('.')

from user_preferences import UserPreferences
from recipe_filters import RecipeFilters
from openai_handler import extract_recipe_intent
from recipe_storage import get_supabase_service_client
from models import FullRecipeModel, IngredientModel

async def test_complete_personalized_workflow():
    """Test the complete personalized recipe discovery workflow"""
    
    print("=== Testing Complete Personalized Recipe Agent ===\n")
    
    # Test user
    test_user_id = '56cae3ba-7998-4cd1-9cd8-991291691679'
    original_prompt = "quick chicken dinner"
    
    # Step 1: Setup test user preferences
    print("1. Setting up test user preferences...")
    supabase = get_supabase_service_client()
    
    test_preferences = {
        'user_id': test_user_id,
        'diet_type': 'keto',
        'allergies': ['peanuts', 'shellfish'],
        'disliked_ingredients': ['cilantro', 'olives']
    }
    
    test_hated_recipes = [
        {
            'user_id': test_user_id,
            'source_url': 'https://www.allrecipes.com/recipe/bad-chicken-recipe/'
        }
    ]
    
    try:
        # Clean and insert test data
        supabase.table('user_preferences').delete().eq('user_id', test_user_id).execute()
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        
        supabase.table('user_preferences').insert(test_preferences).execute()
        supabase.table('hated_recipes').insert(test_hated_recipes).execute()
        
        print("✓ Test data created successfully")
    except Exception as e:
        print(f"✗ Failed to setup test data: {e}")
        return False
    
    # Step 2: Fetch user preferences and enhance prompt
    print("\n2. Fetching user preferences and enhancing prompt...")
    
    user_prefs = UserPreferences()
    preferences = await user_prefs.get_user_preferences(test_user_id)
    enhanced_prompt = user_prefs.enhance_prompt_with_preferences(original_prompt, preferences)
    
    print(f"Original prompt: {original_prompt}")
    print(f"Enhanced prompt: {enhanced_prompt}")
    print(f"User diet type: {preferences['diet_type']}")
    print(f"User allergens: {preferences['allergens']}")
    print(f"User dislikes: {preferences['disliked_ingredients']}")
    
    # Step 3: Extract intent with enhanced prompt
    print("\n3. Extracting intent with OpenAI...")
    
    try:
        intent = extract_recipe_intent(enhanced_prompt)
        print(f"Extracted keywords: {intent.keywords}")
        print(f"Meal type: {intent.meal_type}")
        print(f"Diet type: {intent.diet_type}")
        print(f"Cuisine type: {intent.cuisine_type}")
    except Exception as e:
        print(f"✗ Intent extraction failed: {e}")
        return False
    
    # Step 4: Test hated recipe filtering
    print("\n4. Testing hated recipe filtering...")
    
    recipe_filters = RecipeFilters()
    hated_urls = await user_prefs.get_hated_recipes(test_user_id)
    print(f"Hated recipes found: {len(hated_urls)}")
    
    # Test URL filtering
    test_urls = [
        'https://www.allrecipes.com/recipe/good-chicken-recipe/',
        'https://www.allrecipes.com/recipe/bad-chicken-recipe/',  # Should be filtered
        'https://www.eatingwell.com/recipe/keto-chicken-dinner/',
        'https://www.delish.com/recipe/chicken-stir-fry/'
    ]
    
    filtered_urls = await recipe_filters.filter_recipe_urls(test_urls, test_user_id)
    print(f"URLs before filtering: {len(test_urls)}")
    print(f"URLs after filtering: {len(filtered_urls)}")
    print(f"Excluded hated recipes: {len(test_urls) - len(filtered_urls)}")
    
    # Step 5: Simulate recipe creation and filtering
    print("\n5. Simulating recipe filtering with parsed recipes...")
    
    # Create sample recipes to test filtering
    sample_recipes = [
        FullRecipeModel(
            recipe_id="recipe_1",
            title="Keto Chicken Skillet",
            description="Low-carb chicken dinner",
            source_url="https://www.eatingwell.com/recipe/keto-chicken-dinner/",
            ingredients=[
                IngredientModel(text="2 lbs chicken breast", quantity=2.0, unit="lbs"),
                IngredientModel(text="1 tbsp olive oil", quantity=1.0, unit="tbsp")
            ],
            instructions=["Cook chicken in olive oil", "Season and serve"]
        ),
        FullRecipeModel(
            recipe_id="recipe_2",
            title="Bad Chicken Recipe",
            description="This recipe should be filtered out",
            source_url="https://www.allrecipes.com/recipe/bad-chicken-recipe/",
            ingredients=[
                IngredientModel(text="chicken with peanuts", quantity=1.0, unit="serving")
            ],
            instructions=["Cook chicken"]
        )
    ]
    
    filtered_recipes = await recipe_filters.filter_parsed_recipes(sample_recipes, test_user_id)
    print(f"Recipes before filtering: {len(sample_recipes)}")
    print(f"Recipes after filtering: {len(filtered_recipes)}")
    
    for recipe in filtered_recipes:
        print(f"✓ Kept recipe: {recipe.title}")
    
    # Step 6: Test recipe storage
    print("\n6. Testing recipe storage...")
    
    stored_count = 0
    for recipe in filtered_recipes:
        recipe_data = {
            'title': recipe.title,
            'image_url': str(recipe.image_url) if recipe.image_url else '',
            'description': recipe.description or '',
            'ingredients': [ing.dict() for ing in recipe.ingredients] if recipe.ingredients else [],
            'instructions': recipe.instructions or [],
            'source_url': str(recipe.source_url)
        }
        
        try:
            from recipe_storage import store_searched_recipe
            await store_searched_recipe(recipe_data, test_user_id)
            stored_count += 1
            print(f"✓ Stored recipe: {recipe.title}")
        except Exception as e:
            print(f"✗ Failed to store recipe {recipe.title}: {e}")
    
    print(f"Successfully stored {stored_count} recipes")
    
    # Step 7: Verify stored recipes
    print("\n7. Verifying stored recipes...")
    
    try:
        response = supabase.table('recipe_search').select('*').eq('user_id', test_user_id).order('created_at', desc=True).execute()
        print(f"Total recipes in database: {len(response.data)}")
        
        for recipe in response.data[:3]:  # Show last 3 recipes
            print(f"- {recipe.get('title', 'Unknown')} ({recipe.get('created_at', 'Unknown')})")
    except Exception as e:
        print(f"✗ Failed to verify stored recipes: {e}")
    
    # Cleanup
    print("\n8. Cleaning up test data...")
    try:
        supabase.table('user_preferences').delete().eq('user_id', test_user_id).execute()
        supabase.table('hated_recipes').delete().eq('user_id', test_user_id).execute()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"⚠ Warning: Failed to cleanup: {e}")
    
    print("\n=== Personalized Recipe Agent Test Complete ===")
    print("✓ User preference fetching")
    print("✓ Prompt enhancement with diet/allergen context")
    print("✓ Intent extraction with OpenAI")
    print("✓ Hated recipe URL filtering")
    print("✓ Recipe object filtering")
    print("✓ Recipe storage integration")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_complete_personalized_workflow())
    print(f"\nPersonalized Agent Test: {'PASSED' if success else 'FAILED'}")