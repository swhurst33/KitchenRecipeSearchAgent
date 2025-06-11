"""
Main FastAPI app for Kitchnsync Recipe Discovery Agent
Backend-only service triggered by webhook from RecipeSearchPage frontend
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AgentRequest, AgentResponse, RecipeResponse
from openai_handler import extract_recipe_intent
from recipe_scraper import RecipeScraper
from recipe_storage import RecipeStorage, store_searched_recipe
from user_preferences import UserContextLoader
from recipe_filters import RecipeFilters
from prompt_enricher import PromptEnricher
from recipe_crawler import RecipeCrawler
from recipe_bulk_storage import RecipeBulkStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kitchnsync Recipe Discovery Agent",
    description="AI-powered backend agent for recipe discovery and meal planning",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
recipe_scraper = RecipeScraper()
recipe_storage = RecipeStorage()

@app.get("/")
def root():
    """Root endpoint - API documentation"""
    return {
        "service": "Kitchnsync Recipe Discovery Agent",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health - Service health check",
            "agent": "POST /agent - Recipe discovery endpoint"
        },
        "example": {
            "url": "/agent",
            "method": "POST",
            "body": {
                "prompt": "quick keto dinner",
                "user_id": "user123"
            }
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Kitchnsync Recipe Agent", "version": "2.0.0"}

@app.post("/agent", response_model=AgentResponse)
async def recipe_discovery_agent(request: AgentRequest):
    """
    Main agent endpoint triggered by webhook from RecipeSearchPage frontend
    
    Steps:
    1. Extract intent using OpenAI GPT-4
    2. Get recipe sources from Supabase
    3. Filter out hated recipes
    4. Scrape and parse recipe pages
    5. Return first 10 recipes (title, image, description) to frontend
    6. Store full recipe data in Supabase for MealPlanner module
    """
    try:
        logger.info(f"Processing recipe request for user {request.user_id}: {request.prompt}")
        
        # Step 1: Load user context from new table structure
        context_loader = UserContextLoader()
        user_context = await context_loader.load_user_context(request.user_id)
        
        # Step 2: Task 3 - Enrich prompt and extract search keywords using OpenAI
        prompt_enricher = PromptEnricher()
        enrichment_result = prompt_enricher.process_prompt_for_search(request.prompt, user_context)
        
        enriched_prompt = enrichment_result['enriched_prompt']
        search_keywords = enrichment_result['search_keywords']
        
        logger.info(f"Enriched prompt: {enriched_prompt}")
        logger.info(f"Extracted search keywords: {search_keywords}")
        
        # Step 3: Extract intent using OpenAI with enriched prompt
        intent = extract_recipe_intent(enriched_prompt)
        logger.info(f"Extracted intent from enriched prompt: {intent}")
        
        # Step 3: Initialize recipe filters
        recipe_filters = RecipeFilters()
        
        # Step 4: Task 4 - Crawl pages and scrape recipes using new crawler
        recipe_crawler = RecipeCrawler()
        recipes_data = await recipe_crawler.crawl_and_scrape_recipes(
            enriched_prompt=enriched_prompt,
            max_recipes=10
        )
        
        if not recipes_data:
            logger.warning(f"No recipes found for user {request.user_id}, prompt: {request.prompt}")
            return AgentResponse(
                recipes=[],
                message="No recipes found for your request. Please try different search terms."
            )
        
        # Step 5: Apply filtering and prepare response from Task 4 data
        response_recipes = []
        stored_count = 0
        
        for recipe_dict in recipes_data:
            # Apply URL filtering for hated recipes
            source_url = recipe_dict.get('source_url', '')
            user_context = await context_loader.load_user_context(request.user_id)
            excluded_urls = set(user_context.get('excluded_urls', []))
            
            if source_url in excluded_urls:
                logger.info(f"Filtered out hated recipe: {recipe_dict.get('title', 'Unknown')}")
                continue
            
            # Store in recipe_search table using Task 4 format
            try:
                await store_searched_recipe(recipe_data, request.user_id)
                stored_count += 1
                logger.info(f"✓ Stored recipe '{recipe.title}' for user {request.user_id}")
            except Exception as e:
                logger.error(f"✗ Failed to store recipe '{recipe.title}' for user {request.user_id}: {e}")
                # Continue processing other recipes even if one fails
            
            # Add to response (only basic fields for frontend)
            response_recipes.append({
                "title": recipe.title,
                "image_url": recipe.image_url,
                "description": recipe.description,
                "recipe_id": recipe.recipe_id
            })
        
        logger.info(f"Storage summary: {stored_count}/{len(recipes)} recipes stored in recipe_search table")
        
        logger.info(f"Successfully processed request: found {len(recipes)} recipes")
        
        return AgentResponse(
            recipes=response_recipes,
            message=f"Found {len(recipes)} recipes for '{request.prompt}'"
        )
        
    except Exception as e:
        logger.error(f"Error processing recipe request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process recipe request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)