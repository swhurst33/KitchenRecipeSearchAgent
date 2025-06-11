"""
Legacy recipe storage functions - maintained for backward compatibility
Note: Primary storage now handled by RecipeBulkStorage system
"""

import logging
import os
from typing import Dict, Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """Initialize Supabase client with anon key"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
        )

    return create_client(url, key)


def get_supabase_service_client() -> Client:
    """Initialize Supabase client with service role key for bypassing RLS"""
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set"
        )

    return create_client(url, service_key)


async def store_searched_recipe(recipe_data: Dict[str, Any], user_id: str) -> None:
    """
    Store a single searched recipe in the recipe_search table
    """
    try:
        # Use service role key to bypass RLS for inserting data
        supabase = get_supabase_service_client()

        # Prepare data for recipe_search table
        search_data = {
            "user_id": user_id,
            "title": recipe_data.get("title", ""),
            "image_url": recipe_data.get("image_url", ""),
            "description": recipe_data.get("description", ""),
            "ingredients": recipe_data.get("ingredients", []),
            "instructions": recipe_data.get("instructions", []),
            "source_url": recipe_data.get("source_url", ""),
        }

        # Insert into recipe_search table
        response = supabase.table("recipe_search").insert(search_data).execute()

        if response.data:
            logger.info(
                f"Successfully stored recipe '{recipe_data.get('title', 'Unknown')}' for user {user_id}"
            )
        else:
            logger.warning(
                f"No data returned when storing recipe '{recipe_data.get('title', 'Unknown')}'"
            )

    except Exception as e:
        logger.error(
            f"Failed to store recipe '{recipe_data.get('title', 'Unknown')}' for user {user_id}: {e}"
        )
        # Don't raise exception - storage failure shouldn't break the response


# RecipeStorage class removed - replaced by RecipeBulkStorage system
