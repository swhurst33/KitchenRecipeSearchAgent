"""
Supabase integration for fetching recipe sources
"""

import os
import logging
from typing import List
from models import RecipeSource

logger = logging.getLogger(__name__)

# Mock implementation for demonstration - in production, use actual Supabase client
async def get_recipe_sources() -> List[str]:
    """
    Fetch active recipe sources from Supabase recipe_sources table
    Returns list of domain names for recipe scraping
    """
    try:
        # In production, this would query Supabase:
        # supabase = create_client(url, key)
        # response = supabase.table('recipe_sources').select('*').eq('is_active', True).execute()
        
        # For now, return curated list of reliable recipe sources
        return [
            'allrecipes.com',
            'eatingwell.com',
            'foodnetwork.com',
            'simplyrecipes.com',
            'tasteofhome.com',
            'recipetineats.com'
        ]
        
    except Exception as e:
        logger.error(f"Error fetching recipe sources: {e}")
        # Fallback to default sources
        return ['allrecipes.com', 'eatingwell.com', 'foodnetwork.com']