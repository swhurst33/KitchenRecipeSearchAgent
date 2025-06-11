"""
Task 5: Bulk Recipe Storage System
Handles bulk insertion of recipes into recipe_search table with user cleanup
"""

import logging
import os
from typing import List, Dict, Any
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class RecipeBulkStorage:
    """Handles bulk recipe insertion with user cleanup for Task 5"""
    
    def __init__(self):
        self.supabase = self._get_supabase_service_client()
    
    def _get_supabase_service_client(self) -> Client:
        """Initialize Supabase client with service role key for bypassing RLS"""
        url = os.environ.get("SUPABASE_URL")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set")
        
        return create_client(url, service_key)
    
    async def insert_recipes_bulk(self, recipes_data: List[Dict[str, Any]], user_id: str) -> int:
        """
        Task 5: Insert up to 10 valid recipes into recipe_search table
        
        Steps:
        1. Delete previous rows for the user_id
        2. Bulk insert new recipes with all required fields
        3. Return count of successfully inserted recipes
        
        Args:
            recipes_data: List of recipe dictionaries from Task 4 crawler
            user_id: User ID for the recipes
            
        Returns:
            Number of successfully inserted recipes
        """
        try:
            # Step 1: Delete previous rows for this user_id
            await self._delete_user_previous_searches(user_id)
            
            # Step 2: Prepare recipes for bulk insertion (max 10)
            recipes_to_insert = recipes_data[:10]  # Limit to 10 as specified
            
            if not recipes_to_insert:
                logger.warning(f"No recipes to insert for user {user_id}")
                return 0
            
            # Step 3: Format recipes for recipe_search table
            formatted_recipes = []
            current_time = datetime.utcnow().isoformat()
            
            for recipe in recipes_to_insert:
                formatted_recipe = self._format_recipe_for_insertion(recipe, user_id, current_time)
                if formatted_recipe:
                    formatted_recipes.append(formatted_recipe)
            
            if not formatted_recipes:
                logger.warning(f"No valid recipes to insert for user {user_id}")
                return 0
            
            # Step 4: Bulk insert recipes
            response = self.supabase.table('recipe_search').insert(formatted_recipes).execute()
            
            inserted_count = len(response.data) if response.data else 0
            logger.info(f"Successfully bulk inserted {inserted_count} recipes for user {user_id}")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error in bulk recipe insertion for user {user_id}: {e}")
            return 0
    
    async def _delete_user_previous_searches(self, user_id: str) -> None:
        """Delete previous recipe_search rows for the user to keep only latest search"""
        try:
            response = self.supabase.table('recipe_search').delete().eq('user_id', user_id).execute()
            
            deleted_count = len(response.data) if response.data else 0
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} previous recipe searches for user {user_id}")
            else:
                logger.info(f"No previous recipe searches found for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error deleting previous searches for user {user_id}: {e}")
            # Continue with insertion even if deletion fails
    
    def _format_recipe_for_insertion(self, recipe: Dict[str, Any], user_id: str, created_at: str) -> Dict[str, Any]:
        """
        Format recipe data for recipe_search table insertion
        
        Required fields: user_id, title, description, image_url, ingredients, 
                        instructions, macros, servings, source_url, site_name, created_at
        """
        try:
            formatted = {
                'user_id': user_id,
                'title': recipe.get('title', '').strip(),
                'description': recipe.get('description', '').strip(),
                'image_url': recipe.get('image_url', '').strip(),
                'ingredients': recipe.get('ingredients', []),
                'instructions': recipe.get('instructions', []),
                'macros': recipe.get('macros', {}),
                'servings': recipe.get('servings'),
                'source_url': recipe.get('source_url', '').strip(),
                'site_name': recipe.get('site_name', '').strip(),
                'created_at': created_at
            }
            
            # Validate required fields
            if not formatted['title'] or not formatted['source_url']:
                logger.warning(f"Skipping recipe with missing title or source_url: {recipe}")
                return None
            
            # Ensure servings is an integer or null
            if formatted['servings'] is not None:
                try:
                    formatted['servings'] = int(formatted['servings'])
                except (ValueError, TypeError):
                    formatted['servings'] = None
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting recipe for insertion: {e}")
            return None
    
    async def get_user_recipe_searches(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all recipe searches for a user (for testing purposes)"""
        try:
            response = self.supabase.table('recipe_search').select('*').eq('user_id', user_id).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error fetching recipe searches for user {user_id}: {e}")
            return []
    
    async def get_recipe_search_count(self, user_id: str) -> int:
        """Get count of recipe searches for a user"""
        try:
            response = self.supabase.table('recipe_search').select('id', count='exact').eq('user_id', user_id).execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            logger.error(f"Error counting recipe searches for user {user_id}: {e}")
            return 0