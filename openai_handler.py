"""
OpenAI handler for extracting recipe intent and keywords
"""

import os
import json
import logging
from openai import OpenAI
from models import RecipeIntent

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def extract_search_keywords(enriched_prompt: str) -> list[str]:
    """
    Extract 3-5 optimized keywords from enriched prompt for search crawler use
    """
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a search keyword optimization expert for recipe discovery. 
                    Extract 3-5 highly effective keywords from the enriched recipe prompt that will yield the best search results.
                    
                    Focus on:
                    - Main ingredients (chicken, pasta, beef)
                    - Cooking methods (grilled, baked, stir-fry)
                    - Dish types (salad, soup, casserole)
                    - Key descriptors (quick, healthy, spicy)
                    
                    Ignore common words like: recipe, cooking, make, want, need, the, and, or
                    
                    Return a JSON array of 3-5 keywords:
                    ["chicken", "grilled", "mediterranean", "healthy"]"""
                },
                {
                    "role": "user",
                    "content": f"Extract search keywords from: {enriched_prompt}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        content = response.choices[0].message.content or ""
        result = json.loads(content)
        
        # Handle different response formats
        if isinstance(result, list):
            keywords = result
        elif isinstance(result, dict):
            keywords = result.get('keywords', list(result.values())[0] if result else [])
        else:
            keywords = []
            
        # Ensure we have 3-5 keywords
        if len(keywords) < 3:
            fallback_keywords = enriched_prompt.lower().replace(',', ' ').split()
            keywords.extend([k for k in fallback_keywords if k not in keywords and len(k) > 2])
            
        return keywords[:5]  # Limit to 5 keywords
        
    except Exception as e:
        logger.error(f"Error extracting keywords with OpenAI: {e}")
        # Fallback keyword extraction
        words = enriched_prompt.lower().replace(',', ' ').split()
        return [word for word in words if len(word) > 3 and word not in ['recipe', 'cooking', 'make', 'want', 'need']][:5]

def extract_recipe_intent(prompt: str) -> RecipeIntent:
    """
    Extract recipe intent and keywords from user prompt using OpenAI GPT-4
    """
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a culinary intent extraction expert. Analyze the user's recipe prompt and extract:
                    1. meal_type: breakfast, lunch, dinner, snack, dessert, brunch, appetizer
                    2. diet_type: keto, vegetarian, vegan, paleo, gluten-free, dairy-free, low-carb, mediterranean, etc.
                    3. keywords: main ingredients, cooking methods, flavors, specific dishes
                    4. time_constraint: quick, fast, slow, under 30 minutes, one-pot, etc.
                    5. cuisine_type: italian, mexican, asian, indian, american, french, etc.
                    
                    Respond with JSON in this exact format:
                    {
                        "meal_type": "dinner",
                        "diet_type": "keto", 
                        "keywords": ["chicken", "low-carb", "garlic", "pan-seared"],
                        "time_constraint": "quick",
                        "cuisine_type": "italian"
                    }
                    
                    If any field is not clear from the prompt, set it to null."""
                },
                {
                    "role": "user", 
                    "content": f"Extract intent from this recipe prompt: {prompt}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        content = response.choices[0].message.content or ""
        result = json.loads(content)
        
        return RecipeIntent(
            meal_type=result.get("meal_type"),
            diet_type=result.get("diet_type"),
            keywords=result.get("keywords", []),
            time_constraint=result.get("time_constraint"),
            cuisine_type=result.get("cuisine_type")
        )
        
    except Exception as e:
        logger.error(f"Error extracting intent with OpenAI: {e}")
        # Fallback to simple keyword extraction
        keywords = prompt.lower().split()
        return RecipeIntent(
            keywords=keywords,
            meal_type=None,
            diet_type=None,
            time_constraint=None,
            cuisine_type=None
        )