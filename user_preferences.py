"""
User preferences integration for personalized recipe filtering
"""
import logging
from typing import Optional, List, Dict, Any
from supabase import Client
from recipe_storage import get_supabase_service_client

logger = logging.getLogger(__name__)

class UserPreferences:
    def __init__(self):
        self.supabase: Client = get_supabase_service_client()
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user preferences from Supabase user_preferences table
        Returns dict with diet_type, allergens, and disliked_ingredients
        """
        try:
            response = self.supabase.table('user_preferences').select('*').eq('user_id', user_id).execute()
            
            if response.data:
                prefs = response.data[0]
                return {
                    'diet_type': prefs.get('diet_type', ''),
                    'allergens': self._parse_comma_separated(prefs.get('allergies', '')),
                    'disliked_ingredients': self._parse_comma_separated(prefs.get('disliked_ingredients', ''))
                }
            else:
                logger.info(f"No preferences found for user {user_id}")
                return {
                    'diet_type': '',
                    'allergens': [],
                    'disliked_ingredients': []
                }
                
        except Exception as e:
            logger.error(f"Error fetching user preferences for {user_id}: {e}")
            return {
                'diet_type': '',
                'allergens': [],
                'disliked_ingredients': []
            }
    
    async def get_hated_recipes(self, user_id: str) -> List[str]:
        """
        Fetch list of hated recipe URLs for the user
        """
        try:
            response = self.supabase.table('hated_recipes').select('recipe_url').eq('user_id', user_id).execute()
            
            if response.data:
                return [recipe['recipe_url'] for recipe in response.data if recipe.get('recipe_url')]
            else:
                logger.info(f"No hated recipes found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching hated recipes for {user_id}: {e}")
            return []
    
    def _parse_comma_separated(self, text: str) -> List[str]:
        """
        Parse comma-separated string into list of cleaned items
        """
        if not text or not text.strip():
            return []
        
        return [item.strip() for item in text.split(',') if item.strip()]
    
    def enhance_prompt_with_preferences(self, original_prompt: str, preferences: Dict[str, Any]) -> str:
        """
        Enhance the original prompt with user preference context
        """
        enhancements = []
        
        # Add diet type filter
        if preferences.get('diet_type'):
            enhancements.append(f"filtered for a {preferences['diet_type']} diet")
        
        # Add exclusions
        exclusions = []
        if preferences.get('allergens'):
            exclusions.extend(preferences['allergens'])
        if preferences.get('disliked_ingredients'):
            exclusions.extend(preferences['disliked_ingredients'])
        
        if exclusions:
            exclusion_text = ', '.join(exclusions)
            enhancements.append(f"EXCLUDE: {exclusion_text}")
        
        if enhancements:
            enhancement_text = ', '.join(enhancements)
            enhanced_prompt = f"{original_prompt}, {enhancement_text}"
            logger.info(f"Enhanced prompt: {enhanced_prompt}")
            return enhanced_prompt
        
        return original_prompt