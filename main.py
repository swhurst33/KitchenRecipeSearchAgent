import os
import json
import logging
from flask import Flask, request, jsonify, send_file
from flask.logging import default_handler
from openai import OpenAI
from recipe_parser import RecipeParser
from models import AgentRequest, AgentResponse, IntentExtraction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

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
        
        content = response.choices[0].message.content or ""
        result = json.loads(content)
        
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

@app.route("/")
def root():
    """Serve the demo interface"""
    return send_file("demo.html")

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"message": "Kitchnsync Recipe Agent is running", "version": "1.0.0"})

@app.route("/agent", methods=["POST"])
def recipe_agent():
    """
    Main agent endpoint that processes natural language prompts and returns structured recipe data
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Prompt is required"}), 400
        
        prompt = data['prompt']
        logger.info(f"Processing recipe request: {prompt}")
        
        # Step 1: Extract intent and keywords using OpenAI
        intent = extract_intent_and_keywords(prompt)
        logger.info(f"Extracted intent: {intent}")
        
        # Step 2: Search and parse recipes
        recipes = recipe_parser.get_recipes(intent.search_queries, max_recipes=5)
        
        if not recipes:
            logger.warning(f"No recipes found for prompt: {prompt}")
            return jsonify({
                "recipes": [],
                "message": "No recipes found for your request. Please try a different prompt."
            })
        
        logger.info(f"Successfully found {len(recipes)} recipes")
        
        # Convert Pydantic models to dictionaries for JSON response
        recipes_dict = []
        for recipe in recipes:
            recipe_dict = {
                "title": recipe.title,
                "image_url": str(recipe.image_url) if recipe.image_url else None,
                "source_url": str(recipe.source_url),
                "ingredients": [{"text": ing.text, "quantity": ing.quantity, "unit": ing.unit} for ing in recipe.ingredients],
                "instructions": recipe.instructions,
                "macros": {
                    "calories": recipe.macros.calories if recipe.macros else None,
                    "protein": recipe.macros.protein if recipe.macros else None,
                    "fat": recipe.macros.fat if recipe.macros else None,
                    "carbs": recipe.macros.carbs if recipe.macros else None
                } if recipe.macros else None
            }
            recipes_dict.append(recipe_dict)
        
        return jsonify({
            "recipes": recipes_dict,
            "message": f"Found {len(recipes)} recipes for '{prompt}'"
        })
        
    except Exception as e:
        logger.error(f"Error processing recipe request: {e}")
        return jsonify({"error": f"Failed to process recipe request: {str(e)}"}), 500

@app.route("/extract-intent", methods=["POST"])
def extract_intent_endpoint():
    """
    Endpoint to test intent extraction functionality
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Prompt is required"}), 400
        
        intent = extract_intent_and_keywords(data['prompt'])
        
        return jsonify({
            "meal_type": intent.meal_type,
            "diet_type": intent.diet_type,
            "keywords": intent.keywords,
            "time_constraint": intent.time_constraint,
            "search_queries": intent.search_queries
        })
        
    except Exception as e:
        logger.error(f"Error extracting intent: {e}")
        return jsonify({"error": f"Failed to extract intent: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
