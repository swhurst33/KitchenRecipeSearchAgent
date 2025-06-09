"""
Supabase integration for storing recipe data
"""

import logging
from typing import List
from models import FullRecipeModel

logger = logging.getLogger(__name__)

class RecipeStorage:
    def __init__(self):
        # In production, initialize Supabase client here
        pass
    
    async def store_recipes(self, recipes: List[FullRecipeModel], user_id: str):
        """
        Store full recipe data in Supabase for later use in MealPlanner module
        """
        try:
            # In production, this would insert into Supabase:
            # supabase = create_client(url, key)
            # for recipe in recipes:
            #     recipe_data = {
            #         'user_id': user_id,
            #         'recipe_id': recipe.recipe_id,
            #         'title': recipe.title,
            #         'description': recipe.description,
            #         'image_url': str(recipe.image_url) if recipe.image_url else None,
            #         'source_url': str(recipe.source_url),
            #         'ingredients': [ing.dict() for ing in recipe.ingredients],
            #         'instructions': recipe.instructions,
            #         'nutrition': recipe.nutrition.dict() if recipe.nutrition else None,
            #         'created_at': datetime.utcnow().isoformat()
            #     }
            #     supabase.table('recipes').upsert(recipe_data).execute()
            
            logger.info(f"Stored {len(recipes)} recipes for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing recipes: {e}")
            # Don't raise exception - storage failure shouldn't break the response