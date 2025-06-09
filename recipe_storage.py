"""
Supabase integration for storing recipe data
"""

import logging
import os
from typing import List, Dict, Any
from models import FullRecipeModel
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    
    return create_client(url, key)

async def store_searched_recipe(recipe_data: Dict[str, Any], user_id: str) -> None:
    """
    Store a single searched recipe in the recipe_search table
    """
    try:
        supabase = get_supabase_client()
        
        # Prepare data for recipe_search table
        search_data = {
            'user_id': user_id,
            'title': recipe_data.get('title', ''),
            'image_url': recipe_data.get('image_url', ''),
            'description': recipe_data.get('description', ''),
            'ingredients': recipe_data.get('ingredients', []),
            'instructions': recipe_data.get('instructions', []),
            'source_url': recipe_data.get('source_url', '')
        }
        
        # Insert into recipe_search table
        response = supabase.table('recipe_search').insert(search_data).execute()
        
        if response.data:
            logger.info(f"Successfully stored recipe '{recipe_data.get('title', 'Unknown')}' for user {user_id}")
        else:
            logger.warning(f"No data returned when storing recipe '{recipe_data.get('title', 'Unknown')}'")
            
    except Exception as e:
        logger.error(f"Failed to store recipe '{recipe_data.get('title', 'Unknown')}' for user {user_id}: {e}")
        # Don't raise exception - storage failure shouldn't break the response

class RecipeStorage:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def store_recipes(self, recipes: List[FullRecipeModel], user_id: str):
        """
        Store full recipe data in Supabase for later use in MealPlanner module
        """
        try:
            stored_count = 0
            for recipe in recipes:
                try:
                    recipe_data = {
                        'user_id': user_id,
                        'title': recipe.title,
                        'description': recipe.description or '',
                        'image_url': str(recipe.image_url) if recipe.image_url else '',
                        'source_url': str(recipe.source_url),
                        'ingredients': [ing.dict() for ing in recipe.ingredients] if recipe.ingredients else [],
                        'instructions': recipe.instructions or [],
                    }
                    
                    # Store using the new function
                    await store_searched_recipe(recipe_data, user_id)
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Error storing individual recipe {recipe.title}: {e}")
                    continue
            
            logger.info(f"Successfully stored {stored_count}/{len(recipes)} recipes for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing recipes: {e}")
            # Don't raise exception - storage failure shouldn't break the response