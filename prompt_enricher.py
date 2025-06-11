"""
Prompt enrichment system for Task 3: Tag prompts for AI use
Constructs refined search strings and extracts optimized keywords
"""

import logging
from typing import Dict, List
from openai_handler import extract_search_keywords

logger = logging.getLogger(__name__)

class PromptEnricher:
    """Enriches prompts with user context and extracts search keywords"""
    
    def __init__(self):
        pass
    
    def enrich_prompt(self, original_prompt: str, user_context: Dict) -> str:
        """
        Construct a refined search string using the formula:
        prompt = "{original_prompt} {diet_type} EXCLUDE {exclude_ingredients}"
        
        Args:
            original_prompt: User's original recipe request
            user_context: User context with diet_type and exclude_ingredients
            
        Returns:
            Enriched prompt string ready for search
        """
        enriched_parts = [original_prompt]
        
        # Add diet type if specified
        diet_type = user_context.get('diet_type', '').strip()
        if diet_type:
            enriched_parts.append(f"filtered for a {diet_type} diet")
        
        # Add excluded ingredients if any
        exclude_ingredients = user_context.get('exclude_ingredients', [])
        if exclude_ingredients and len(exclude_ingredients) > 0:
            exclude_list = ', '.join(exclude_ingredients)
            enriched_parts.append(f"EXCLUDE: {exclude_list}")
        
        enriched_prompt = ', '.join(enriched_parts)
        logger.info(f"Enriched prompt: '{original_prompt}' → '{enriched_prompt}'")
        
        return enriched_prompt
    
    def extract_keywords_for_search(self, enriched_prompt: str) -> List[str]:
        """
        Extract 3-5 optimized keywords from enriched prompt using OpenAI
        
        Args:
            enriched_prompt: The enriched prompt with user context
            
        Returns:
            List of 3-5 keywords optimized for recipe search crawlers
        """
        keywords = extract_search_keywords(enriched_prompt)
        logger.info(f"Extracted {len(keywords)} search keywords: {keywords}")
        return keywords
    
    def process_prompt_for_search(self, original_prompt: str, user_context: Dict) -> Dict[str, any]:
        """
        Complete prompt processing pipeline for Task 3
        
        Args:
            original_prompt: User's original recipe request
            user_context: User context from Supabase tables
            
        Returns:
            Dictionary containing enriched prompt and search keywords
        """
        # Step 1: Enrich prompt with user context
        enriched_prompt = self.enrich_prompt(original_prompt, user_context)
        
        # Step 2: Extract search keywords using OpenAI
        search_keywords = self.extract_keywords_for_search(enriched_prompt)
        
        result = {
            'original_prompt': original_prompt,
            'enriched_prompt': enriched_prompt,
            'search_keywords': search_keywords,
            'user_context': user_context
        }
        
        logger.info(f"Completed prompt processing for search: {len(search_keywords)} keywords extracted")
        return result