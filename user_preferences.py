"""
User context loading for personalized recipe filtering
Updated to work with user_settings, hated_recipes, and saved_recipes tables
"""

import logging
from typing import Optional, List, Dict, Any
from supabase import Client
from recipe_storage import get_supabase_service_client

logger = logging.getLogger(__name__)


class UserContextLoader:
    def __init__(self):
        self.supabase: Client = get_supabase_service_client()

    async def load_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Load complete user context from Supabase tables.

        Retrieves:
        - diet_type, allergies, disliked_ingredients from user_settings table
        - source_url values from hated_recipes table
        - source_url values from saved_recipes table

        Returns dict with diet_type, exclude_ingredients, and excluded_urls
        """
        try:
            # Get user settings (diet preferences and restrictions)
            settings = await self._get_user_settings(user_id)

            # Get hated recipe URLs
            hated_urls = await self._get_hated_recipe_urls(user_id)

            # Get saved recipe URLs (for reference, not exclusion)
            saved_urls = await self._get_saved_recipe_urls(user_id)

            # Combine allergies and disliked ingredients into exclusion list
            exclude_ingredients = []
            if settings.get("allergies"):
                exclude_ingredients.extend(settings["allergies"])
            if settings.get("disliked_ingredients"):
                exclude_ingredients.extend(settings["disliked_ingredients"])

            # Create user context dict
            context = {
                "diet_type": settings.get("diet_type", ""),
                "exclude_ingredients": exclude_ingredients,
                "excluded_urls": hated_urls,
                "saved_urls": saved_urls,  # Optional: for potential future use
            }

            logger.info(
                f"Loaded user context for {user_id}: diet={context['diet_type']}, "
                f"exclusions={len(exclude_ingredients)}, hated_urls={len(hated_urls)}"
            )

            return context

        except Exception as e:
            logger.error(f"Error loading user context for {user_id}: {e}")
            return {
                "diet_type": "",
                "exclude_ingredients": [],
                "excluded_urls": [],
                "saved_urls": [],
            }

    async def _get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user settings from user_settings table
        """
        try:
            response = (
                self.supabase.table("user_settings")
                .select("diet_type, allergies, disliked_ingredients")
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                settings = response.data[0]
                return {
                    "diet_type": settings.get("diet_type", ""),
                    "allergies": settings.get("allergies", []) or [],
                    "disliked_ingredients": settings.get("disliked_ingredients", [])
                    or [],
                }
            else:
                logger.info(f"No user settings found for user {user_id}")
                return {"diet_type": "", "allergies": [], "disliked_ingredients": []}

        except Exception as e:
            logger.error(f"Error fetching user settings for {user_id}: {e}")
            return {"diet_type": "", "allergies": [], "disliked_ingredients": []}

    async def _get_hated_recipe_urls(self, user_id: str) -> List[str]:
        """
        Fetch list of hated recipe URLs from hated_recipes table
        """
        try:
            response = (
                self.supabase.table("hated_recipes")
                .select("source_url")
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                urls = [
                    recipe["source_url"]
                    for recipe in response.data
                    if recipe.get("source_url")
                ]
                logger.info(f"Found {len(urls)} hated recipes for user {user_id}")
                return urls
            else:
                logger.info(f"No hated recipes found for user {user_id}")
                return []

        except Exception as e:
            logger.error(f"Error fetching hated recipes for {user_id}: {e}")
            return []

    async def _get_saved_recipe_urls(self, user_id: str) -> List[str]:
        """
        Fetch list of saved recipe URLs from saved_recipes table
        """
        try:
            response = (
                self.supabase.table("saved_recipes")
                .select("source_url")
                .eq("user_id", user_id)
                .execute()
            )

            if response.data:
                urls = [
                    recipe["source_url"]
                    for recipe in response.data
                    if recipe.get("source_url")
                ]
                logger.info(f"Found {len(urls)} saved recipes for user {user_id}")
                return urls
            else:
                logger.info(f"No saved recipes found for user {user_id}")
                return []

        except Exception as e:
            logger.error(f"Error fetching saved recipes for {user_id}: {e}")
            return []

    def enhance_prompt_with_context(
        self, original_prompt: str, context: Dict[str, Any]
    ) -> str:
        """
        Enhance the original prompt with user context
        """
        enhancements = []

        # Add diet type filter
        if context.get("diet_type"):
            enhancements.append(f"filtered for a {context['diet_type']} diet")

        # Add ingredient exclusions
        if context.get("exclude_ingredients"):
            exclusion_text = ", ".join(context["exclude_ingredients"])
            enhancements.append(f"EXCLUDE: {exclusion_text}")

        if enhancements:
            enhancement_text = ", ".join(enhancements)
            enhanced_prompt = f"{original_prompt}, {enhancement_text}"
            logger.info(f"Enhanced prompt: {enhanced_prompt}")
            return enhanced_prompt

        return original_prompt


# Backward compatibility class
class UserPreferences:
    """Legacy wrapper for backward compatibility"""

    def __init__(self):
        self.context_loader = UserContextLoader()

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Legacy method - redirects to new context loader"""
        context = await self.context_loader.load_user_context(user_id)
        return {
            "diet_type": context["diet_type"],
            "allergens": context["exclude_ingredients"],
            "disliked_ingredients": [],
        }

    async def get_hated_recipes(self, user_id: str) -> List[str]:
        """Legacy method - redirects to new context loader"""
        context = await self.context_loader.load_user_context(user_id)
        return context["excluded_urls"]

    def enhance_prompt_with_preferences(
        self, original_prompt: str, preferences: Dict[str, Any]
    ) -> str:
        """Legacy method - converts to new context format"""
        context = {
            "diet_type": preferences.get("diet_type", ""),
            "exclude_ingredients": preferences.get("allergens", [])
            + preferences.get("disliked_ingredients", []),
        }
        return self.context_loader.enhance_prompt_with_context(original_prompt, context)
