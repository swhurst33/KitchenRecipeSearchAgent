from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from supabase import create_client, Client
import os
import asyncio

from recipe_crawler import RecipeCrawler  # ✅ Use your real crawler

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing API keys or Supabase credentials in environment.")

client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str
    user_id: str

def extract_keywords_and_intent(prompt: str) -> dict:
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that extracts structured metadata from recipe prompts. "
                "Return a valid JSON object with any of the following keys: "
                "`diet_type`, `included_ingredients`, `excluded_ingredients`, and `cuisine`."
            ),
        },
        {"role": "user", "content": f"Prompt: {prompt}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        return eval(raw) if raw.startswith("{") else {"raw_response": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

def load_user_settings(user_id: str) -> dict:
    try:
        response = supabase \
            .from_("user_settings") \
            .select("*") \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        return response.data or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error (user_settings): {str(e)}")

def merge_settings_and_prompt(user_settings: dict, extracted_metadata: dict) -> dict:
    def merge_lists(key):
        return list(set(
            (user_settings.get(key) or []) +
            (extracted_metadata.get(key) or [])
        ))

    return {
        "diet_type": extracted_metadata.get("diet_type") or user_settings.get("diet_type"),
        "cuisine": extracted_metadata.get("cuisine"),
        "included_ingredients": merge_lists("included_ingredients"),
        "excluded_ingredients": merge_lists("excluded_ingredients") +
                                (user_settings.get("allergies") or []) +
                                (user_settings.get("disliked_ingredients") or [])
    }

# 🔄 Use RecipeCrawler for real crawling
async def run_crawler(prompt: str, disliked_ingredients: list) -> list:
    crawler = RecipeCrawler()
    recipes = await crawler.crawl_and_scrape_recipes(prompt, disliked_ingredients, max_recipes=10)
    return recipes

# ✅ Store full recipe format in Supabase
def store_recipe_matches(user_id: str, prompt: str, recipes: list):
    try:
        rows = []
        for recipe in recipes:
            rows.append({
                "user_id": user_id,
                "title": recipe.get("title"),
                "description": recipe.get("description"),
                "image_url": recipe.get("image_url"),
                "servings": recipe.get("servings"),
                "source_url": recipe.get("source_url"),
                "ingredients": recipe.get("ingredients"),
                "macros": recipe.get("macros"),
                "instructions": recipe.get("instructions"),
                "site_name": recipe.get("site_name")
            })
        if rows:
            supabase.from_("recipe_search").insert(rows).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase insert error: {str(e)}")

@app.post("/agent")
async def agent_crawl_and_match(req: PromptRequest):
    if not req.prompt or not req.user_id:
        raise HTTPException(status_code=400, detail="Missing prompt or user_id")

    extracted = extract_keywords_and_intent(req.prompt)
    user_settings = load_user_settings(req.user_id)
    query_profile = merge_settings_and_prompt(user_settings, extracted)

    enriched_prompt = req.prompt
    disliked_ingredients = query_profile.get("excluded_ingredients", [])

    all_matches = await run_crawler(enriched_prompt, disliked_ingredients)
    store_recipe_matches(req.user_id, req.prompt, all_matches[:10])

    return {
        "status": "success",
        "user_id": req.user_id,
        "original_prompt": req.prompt,
        "query_profile": query_profile,
        "matches_found": len(all_matches),
        "recipes": all_matches[:10]
    }

@app.get("/")
def root():
    return {"message": "Kitchnsync Agent API - Step 7 (Real Recipe Crawling Ready)"}
