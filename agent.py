import os
import json
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from models import AgentRequest, AgentResponse, IntentExtraction
from recipe_parser import RecipeParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kitchnsync Recipe Agent",
    description="AI-powered recipe discovery agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize recipe parser
recipe_parser = RecipeParser()

def extract_intent_and_keywords(prompt: str) -> IntentExtraction:
    """Extract intent and keywords from user prompt using OpenAI"""
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a culinary intent extraction expert. Analyze the user's recipe prompt and extract:
                    1. meal_type (breakfast, lunch, dinner, snack, dessert, etc.)
                    2. diet_type (keto, vegetarian, vegan, paleo, gluten-free, etc.)
                    3. keywords (main ingredients, cooking methods, flavors)
                    4. time_constraint (quick, fast, 30 minutes, slow, etc.)
                    5. search_queries (3-5 optimized search queries for recipe websites)
                    
                    Respond with JSON in this exact format:
                    {
                        "meal_type": "dinner",
                        "diet_type": "keto", 
                        "keywords": ["chicken", "low-carb", "easy"],
                        "time_constraint": "quick",
                        "search_queries": ["keto chicken dinner", "quick low carb chicken", "easy keto chicken recipe"]
                    }"""
                },
                {
                    "role": "user", 
                    "content": f"Extract intent from this recipe prompt: {prompt}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return IntentExtraction(
            meal_type=result.get("meal_type"),
            diet_type=result.get("diet_type"),
            keywords=result.get("keywords", []),
            time_constraint=result.get("time_constraint"),
            search_queries=result.get("search_queries", [prompt])
        )
        
    except Exception as e:
        logger.error(f"Error extracting intent: {e}")
        # Fallback to simple keyword extraction
        return IntentExtraction(
            keywords=[prompt],
            search_queries=[prompt, f"{prompt} recipe", f"easy {prompt}"]
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Kitchnsync Recipe Agent is running", "version": "1.0.0"}

@app.post("/agent", response_model=AgentResponse)
async def recipe_agent(request: AgentRequest):
    """
    Main agent endpoint that processes natural language prompts and returns structured recipe data
    """
    try:
        logger.info(f"Processing recipe request: {request.prompt}")
        
        # Step 1: Extract intent and keywords using OpenAI
        intent = extract_intent_and_keywords(request.prompt)
        logger.info(f"Extracted intent: {intent}")
        
        # Step 2: Search and parse recipes
        recipes = recipe_parser.get_recipes(intent.search_queries, max_recipes=5)
        
        if not recipes:
            logger.warning(f"No recipes found for prompt: {request.prompt}")
            return AgentResponse(
                recipes=[],
                message="No recipes found for your request. Please try a different prompt."
            )
        
        logger.info(f"Successfully found {len(recipes)} recipes")
        
        return AgentResponse(
            recipes=recipes,
            message=f"Found {len(recipes)} recipes for '{request.prompt}'"
        )
        
    except Exception as e:
        logger.error(f"Error processing recipe request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process recipe request: {str(e)}"
        )

@app.post("/extract-intent")
async def extract_intent_endpoint(request: AgentRequest):
    """
    Endpoint to test intent extraction functionality
    """
    try:
        intent = extract_intent_and_keywords(request.prompt)
        return intent
    except Exception as e:
        logger.error(f"Error extracting intent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract intent: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
