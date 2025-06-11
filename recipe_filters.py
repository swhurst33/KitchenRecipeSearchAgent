"""
Recipe filtering system for personalized results
"""
import logging
from typing import List, Set
from models import FullRecipeModel
from user_preferences import UserContextLoader

logger = logging.getLogger(__name__)

class RecipeFilters:
    def __init__(self):
        self.context_loader = UserContextLoader()
    
    async def filter_recipe_urls(self, recipe_urls: List[str], user_id: str) -> List[str]:
        """
        Filter out hated recipe URLs before parsing
        """
        if not recipe_urls:
            return []
        
        try:
            user_context = await self.context_loader.load_user_context(user_id)
            hated_urls_set = set(user_context['excluded_urls'])
            
            filtered_urls = [url for url in recipe_urls if url not in hated_urls_set]
            
            excluded_count = len(recipe_urls) - len(filtered_urls)
            if excluded_count > 0:
                logger.info(f"Excluded {excluded_count} hated recipes for user {user_id}")
            
            return filtered_urls
            
        except Exception as e:
            logger.error(f"Error filtering hated recipes for user {user_id}: {e}")
            return recipe_urls  # Return original list if filtering fails
    
    async def filter_parsed_recipes(self, recipes: List[FullRecipeModel], user_id: str) -> List[FullRecipeModel]:
        """
        Additional filtering of parsed recipes based on hated URLs
        (Double-check in case URLs were missed in initial filtering)
        """
        if not recipes:
            return []
        
        try:
            user_context = await self.context_loader.load_user_context(user_id)
            hated_urls_set = set(user_context['excluded_urls'])
            
            filtered_recipes = []
            for recipe in recipes:
                if str(recipe.source_url) not in hated_urls_set:
                    filtered_recipes.append(recipe)
                else:
                    logger.info(f"Filtered out hated recipe: {recipe.title}")
            
            return filtered_recipes
            
        except Exception as e:
            logger.error(f"Error filtering parsed recipes for user {user_id}: {e}")
            return recipes  # Return original list if filtering fails