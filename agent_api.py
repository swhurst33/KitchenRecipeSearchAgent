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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Kitchnsync Recipe Discovery Agent",
    description=
    "AI-powered backend agent for recipe discovery and meal planning",
    version="2.0.0",
)

# ✅ Allow frontend origin only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← TEMP fix for Replit CORS issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Preflight OPTIONS request for CORS
@app.options("/agent")
async def preflight_handler():
    return JSONResponse(status_code=200, content={"ok": True})


# ✅ Main agent handler
@app.post("/agent", response_model=AgentResponse)
async def recipe_discovery_agent(request: AgentRequest):
    try:
        logger.info(
            f"📥 Prompt received for user {request.user_id}: {request.prompt}")

        # Step 1: Load user preferences
        context_loader = UserContextLoader()
        user_context = await context_loader.load_user_context(request.user_id)

        # Step 2: Enrich prompt and extract keywords
        prompt_enricher = PromptEnricher()
        enrichment_result = prompt_enricher.process_prompt_for_search(
            request.prompt, user_context)

        enriched_prompt = enrichment_result["enriched_prompt"]
        search_keywords = enrichment_result["search_keywords"]
        logger.info(f"🔍 Enriched prompt: {enriched_prompt}")
        logger.info(f"🔑 Search keywords: {search_keywords}")

        # Step 3: Extract intent
        intent = extract_recipe_intent(enriched_prompt)
        logger.info(f"🧠 Intent: {intent}")

        # Step 4: Crawl and scrape recipes
        recipe_crawler = RecipeCrawler()
        recipes_data = await recipe_crawler.crawl_and_scrape_recipes(
            enriched_prompt=enriched_prompt, max_recipes=10)

        if not recipes_data:
            logger.warning("⚠️ No recipes found.")
            return AgentResponse(
                recipes=[],
                message="No recipes found. Try different search terms.",
            )

        # Step 5: Filter out disliked recipes
        excluded_urls = set(user_context.get("excluded_urls", []))
        filtered_recipes = [
            r for r in recipes_data
            if r.get("source_url", "") not in excluded_urls
        ]

        # Step 6: Save to Supabase
        bulk_storage = RecipeBulkStorage()
        stored_count = await bulk_storage.insert_recipes_bulk(
            filtered_recipes, request.user_id)

        # Step 7: Log the activity
        try:
            log_agent_activity(request.user_id, request.prompt, stored_count)
        except Exception as e:
            logger.error(f"📝 Logging failed: {e}")

        # Step 8: Format response
        response_recipes = []
        for r in filtered_recipes[:10]:
            image_url = r.get("image_url")
            if not image_url or image_url.strip() == "":
                image_url = None
            response_recipes.append(
                RecipeResponse(
                    title=r.get("title", ""),
                    image_url=image_url,
                    description=r.get("description", ""),
                    recipe_id=r.get("source_url", ""),
                ))

        logger.info(f"✅ Returning {len(response_recipes)} recipes to frontend")

        return AgentResponse(
            recipes=response_recipes,
            message=f"Found {len(response_recipes)} recipes"
            if response_recipes else None,
        )

    except Exception as e:
        logger.error(f"💥 Agent failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")
