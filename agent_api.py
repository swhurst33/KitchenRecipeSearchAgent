"""
Main FastAPI app for Kitchnsync Recipe Discovery Agent
Backend-only service triggered by webhook from RecipeSearchPage frontend
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import AgentRequest, AgentResponse, RecipeResponse
from openai_handler import extract_recipe_intent
from user_preferences import UserContextLoader
from prompt_enricher import PromptEnricher
from recipe_crawler import RecipeCrawler
from recipe_bulk_storage import RecipeBulkStorage
from agent_logger import log_agent_activity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kitchnsync Recipe Discovery Agent",
    description=
    "AI-powered backend agent for recipe discovery and meal planning",
    version="2.0.0",
)

# ✅ Standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Replace * with your frontend dev URL
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# ✅ Fallback CORS header injection (works around Replit/Cloudflare bugs)
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


# ✅ Explicit preflight handler
@app.options("/agent")
async def preflight_handler():
    return JSONResponse(content={"status": "ok"})


@app.get("/")
def root():
    return {
        "service": "Kitchnsync Recipe Discovery Agent",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health - Service health check",
            "agent": "POST /agent - Recipe discovery endpoint",
        },
        "example": {
            "url": "/agent",
            "method": "POST",
            "body": {
                "prompt": "quick keto dinner",
                "user_id": "user123"
            },
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Kitchnsync Recipe Agent",
        "version": "2.0.0",
    }


@app.post("/agent", response_model=AgentResponse)
async def recipe_discovery_agent(request: AgentRequest):
    try:
        logger.info(
            f"Processing recipe request for user {request.user_id}: {request.prompt}"
        )

        # Step 1: Load user preferences
        context_loader = UserContextLoader()
        user_context = await context_loader.load_user_context(request.user_id)

        # Step 2: Enrich prompt & extract search keywords
        prompt_enricher = PromptEnricher()
        enrichment_result = prompt_enricher.process_prompt_for_search(
            request.prompt, user_context)

        enriched_prompt = enrichment_result["enriched_prompt"]
        search_keywords = enrichment_result["search_keywords"]
        logger.info(f"Enriched prompt: {enriched_prompt}")
        logger.info(f"Extracted keywords: {search_keywords}")

        # Step 3: Extract intent
        intent = extract_recipe_intent(enriched_prompt)
        logger.info(f"Extracted intent: {intent}")

        # Step 4: Crawl pages
        recipe_crawler = RecipeCrawler()
        recipes_data = await recipe_crawler.crawl_and_scrape_recipes(
            enriched_prompt=enriched_prompt, max_recipes=10)

        if not recipes_data:
            logger.warning("No recipes found.")
            return AgentResponse(
                recipes=[],
                message="No recipes found. Try different search terms.",
            )

        # Step 5: Filter out user-hated recipes
        excluded_urls = set(user_context.get("excluded_urls", []))
        filtered_recipes = [
            r for r in recipes_data
            if r.get("source_url", "") not in excluded_urls
        ]

        # Step 6: Store to Supabase
        bulk_storage = RecipeBulkStorage()
        stored_count = await bulk_storage.insert_recipes_bulk(
            filtered_recipes, request.user_id)

        # Step 7: Log the agent run
        try:
            log_agent_activity(request.user_id, request.prompt, stored_count)
        except Exception as e:
            logger.error(f"Logging failed: {e}")

        # Step 8: Prepare frontend response
        response_recipes = [
            RecipeResponse(
                title=r.get("title", ""),
                image_url=r.get("image_url"),
                description=r.get("description", ""),
                recipe_id=r.get("source_url", ""),
            ) for r in filtered_recipes[:10]
        ]

        logger.info(f"Returning {len(response_recipes)} recipes")

        return AgentResponse(
            recipes=response_recipes,
            message=f"Found {len(response_recipes)} recipes"
            if response_recipes else None,
        )

    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
