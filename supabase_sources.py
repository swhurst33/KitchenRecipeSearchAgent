"""
Supabase integration for fetching recipe sources
"""

import os
import logging
from typing import List, Dict
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    
    return create_client(url, key)

async def get_active_recipe_sources() -> List[Dict[str, str]]:
    """
    Fetch active recipe sources from Supabase recipe_sources table
    Returns list of active source configurations with URL templates
    """
    try:
        supabase = get_supabase_client()
        
        # Query active recipe sources from Supabase
        response = supabase.table('recipe_sources').select(
            'id, site_name, url_template, is_active'
        ).eq('is_active', True).execute()
        
        if response.data:
            logger.info(f"Fetched {len(response.data)} active recipe sources from Supabase")
            return response.data
        else:
            logger.warning("No active recipe sources found in Supabase")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching recipe sources from Supabase: {e}")
        return []  # Return empty list instead of raising to prevent agent failure

def build_search_urls(enhanced_prompt: str, sources: List[Dict[str, str]]) -> List[str]:
    """
    Build search URLs from recipe sources and enhanced prompt with user context
    
    Args:
        enhanced_prompt: User prompt enhanced with diet_type and EXCLUDE ingredients
        sources: List of active recipe sources from Supabase
        
    Returns:
        List of formatted search URLs with {query} replaced
    """
    urls = []
    
    # Format the enhanced prompt for URL encoding
    formatted_query = enhanced_prompt.replace(' ', '+')
    
    for source in sources:
        url_template = source.get('url_template', '')
        site_name = source.get('site_name', 'Unknown')
        
        if '{query}' in url_template:
            search_url = url_template.format(query=formatted_query)
            urls.append(search_url)
            logger.info(f"Built search URL for {site_name}: {search_url}")
        else:
            logger.warning(f"Invalid URL template for {site_name}: {url_template} (missing {{query}} placeholder)")
    
    return urls