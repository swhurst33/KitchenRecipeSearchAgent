"""
Main FastAPI app for Kitchnsync Recipe Discovery Agent
Backend-only service triggered by webhook from RecipeSearchPage frontend
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AgentRequest, AgentResponse
from openai_handler import extract_recipe_intent
from recipe_scraper import RecipeScraper
from recipe_storage import RecipeStorage

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
        
        # Step 1: Extract intent using OpenAI
        intent = extract_recipe_intent(request.prompt)
        logger.info(f"Extracted intent: {intent}")
        
        # Step 2-4: Scrape recipes based on intent
        recipes = await recipe_scraper.find_recipes(
            keywords=intent.keywords,
            meal_type=intent.meal_type,
            diet_type=intent.diet_type,
            user_id=request.user_id,
            max_recipes=10
        )
        
        if not recipes:
            logger.warning(f"No recipes found for user {request.user_id}, prompt: {request.prompt}")
            return AgentResponse(
                recipes=[],
                message="No recipes found for your request. Please try different search terms."
            )
        
        # Step 5: Prepare response with title, image, description only
        response_recipes = []
        for recipe in recipes:
            response_recipes.append({
                "title": recipe.title,
                "image_url": recipe.image_url,
                "description": recipe.description,
                "recipe_id": recipe.recipe_id
            })
        
        # Step 6: Store full recipe data in Supabase (async)
        await recipe_storage.store_recipes(recipes, request.user_id)
        
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