"""
Supabase integration for filtering hated recipes
"""

import logging
from typing import List
from models import FullRecipeModel, HatedRecipe

logger = logging.getLogger(__name__)

async def filter_hated_recipes(recipes: List[FullRecipeModel], user_id: str) -> List[FullRecipeModel]:
    """
    Filter out recipes that the user has marked as hated
    """
    try:
        # In production, this would query Supabase:
        # supabase = create_client(url, key)
        # response = supabase.table('hated_recipes').select('*').eq('user_id', user_id).execute()
        # hated_recipes = response.data
        
        # For now, return all recipes as no filtering is needed without real data
        return recipes
        
    except Exception as e:
        logger.error(f"Error filtering hated recipes: {e}")
        return recipes