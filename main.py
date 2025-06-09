import os
import json
import logging
import asyncio
from flask import Flask, request, jsonify
from openai import OpenAI
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app (compatible with Gunicorn)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class RecipeAgent:
    def __init__(self):
        self.session = httpx.Client(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        # Real recipe website search patterns - using authentic sources
        self.search_patterns = [
            'https://www.allrecipes.com/search/results/?search={query}',
            'https://www.eatingwell.com/search?q={query}',
            'https://www.foodnetwork.com/search/{query}',
        ]

    def extract_intent(self, prompt: str) -> dict:
        """Extract recipe intent using OpenAI"""
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract recipe search intent from the prompt. Return JSON with:
                        - meal_type: breakfast/lunch/dinner/snack/dessert
                        - diet_type: keto/vegetarian/vegan/paleo/gluten-free etc
                        - keywords: main ingredients and cooking methods
                        - cuisine_type: italian/mexican/asian etc
                        """
                    },
                    {"role": "user", "content": f"Extract intent: {prompt}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return {"keywords": prompt.split(), "meal_type": None, "diet_type": None}

    def search_real_recipes(self, query: str, max_results: int = 10) -> list:
        """Search for real recipes from authentic cooking websites"""
        all_recipes = []
        
        for search_url_template in self.search_patterns:
            try:
                search_url = search_url_template.format(query=query.replace(' ', '+'))
                response = self.session.get(search_url)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                recipe_urls = self._extract_recipe_urls(soup, search_url)
                
                # Parse each recipe URL found
                for recipe_url in recipe_urls[:5]:  # Limit per source
                    recipe_data = self._parse_recipe_page(recipe_url)
                    if recipe_data:
                        all_recipes.append(recipe_data)
                        
                if len(all_recipes) >= max_results:
                    break
                    
            except Exception as e:
                logger.error(f"Search error for {search_url_template}: {e}")
                continue
        
        return all_recipes[:max_results]

    def _extract_recipe_urls(self, soup: BeautifulSoup, base_url: str) -> list:
        """Extract recipe URLs from search results"""
        urls = []
        
        if 'allrecipes.com' in base_url:
            # AllRecipes specific URL pattern
            links = soup.find_all('a', href=re.compile(r'/recipe/\d+'))
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin('https://www.allrecipes.com', href)
                    urls.append(full_url)
                    
        elif 'eatingwell.com' in base_url:
            # EatingWell specific URL pattern
            links = soup.find_all('a', href=re.compile(r'/recipe/'))
            for link in links:
                href = link.get('href')
                if href and '/recipe/' in href:
                    full_url = urljoin('https://www.eatingwell.com', href)
                    urls.append(full_url)
                    
        elif 'foodnetwork.com' in base_url:
            # Food Network specific URL pattern
            links = soup.find_all('a', href=re.compile(r'/recipes/'))
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin('https://www.foodnetwork.com', href)
                    urls.append(full_url)
        
        return list(set(urls))  # Remove duplicates

    def _parse_recipe_page(self, url: str) -> dict:
        """Parse individual recipe page for structured data"""
        try:
            response = self.session.get(url)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try Schema.org JSON-LD first (most reliable)
            recipe_data = self._extract_jsonld_recipe(soup)
            if recipe_data:
                return self._format_recipe_response(recipe_data, url)
            
            # Fallback to HTML parsing
            return self._extract_html_recipe(soup, url)
            
        except Exception as e:
            logger.error(f"Failed to parse recipe {url}: {e}")
            return None

    def _extract_jsonld_recipe(self, soup: BeautifulSoup) -> dict:
        """Extract recipe from Schema.org JSON-LD (most reliable method)"""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string or '{}')
                
                # Handle different JSON-LD structures
                if isinstance(data, list):
                    for item in data:
                        if self._is_recipe_schema(item):
                            return item
                elif isinstance(data, dict):
                    if self._is_recipe_schema(data):
                        return data
                    # Check nested structures
                    if '@graph' in data:
                        for item in data['@graph']:
                            if self._is_recipe_schema(item):
                                return item
                                
            except (json.JSONDecodeError, TypeError):
                continue
                
        return None

    def _is_recipe_schema(self, data: dict) -> bool:
        """Check if data is a Recipe schema"""
        if not isinstance(data, dict):
            return False
        type_field = data.get('@type', '')
        return (type_field == 'Recipe' or 
                (isinstance(type_field, list) and 'Recipe' in type_field))

    def _extract_html_recipe(self, soup: BeautifulSoup, url: str) -> dict:
        """Fallback HTML parsing when JSON-LD not available"""
        try:
            title = self._find_recipe_title(soup)
            description = self._find_recipe_description(soup)
            image_url = self._find_recipe_image(soup, url)
            
            if not title:
                return None
                
            return {
                "title": title,
                "description": description,
                "image_url": image_url,
                "recipe_id": hashlib.md5(url.encode()).hexdigest()[:8],
                "source_url": url
            }
            
        except Exception as e:
            logger.error(f"HTML parsing failed for {url}: {e}")
            return None

    def _find_recipe_title(self, soup: BeautifulSoup) -> str:
        """Find recipe title using multiple selectors"""
        selectors = [
            'h1[itemprop="name"]',
            'h1.recipe-title', 
            '.recipe-header h1',
            '.entry-title',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ""

    def _find_recipe_description(self, soup: BeautifulSoup) -> str:
        """Find recipe description"""
        selectors = [
            '[itemprop="description"]',
            '.recipe-description',
            '.recipe-summary',
            'meta[name="description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                return element.get_text(strip=True)
        return ""

    def _find_recipe_image(self, soup: BeautifulSoup, base_url: str) -> str:
        """Find recipe image URL"""
        selectors = [
            'img[itemprop="image"]',
            '.recipe-image img',
            '.recipe-photo img'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src') or element.get('data-src')
                if src:
                    return urljoin(base_url, src)
        return ""

    def _format_recipe_response(self, recipe_data: dict, url: str) -> dict:
        """Format Schema.org recipe data for response"""
        try:
            # Extract image URL
            image = recipe_data.get('image', '')
            if isinstance(image, list) and image:
                image_url = image[0] if isinstance(image[0], str) else image[0].get('url', '')
            elif isinstance(image, dict):
                image_url = image.get('url', '')
            else:
                image_url = str(image) if image else ''

            return {
                "title": recipe_data.get('name', ''),
                "description": recipe_data.get('description', ''),
                "image_url": image_url,
                "recipe_id": hashlib.md5(url.encode()).hexdigest()[:8],
                "source_url": url
            }
            
        except Exception as e:
            logger.error(f"Recipe formatting error: {e}")
            return None

# Initialize the agent
recipe_agent = RecipeAgent()

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Kitchnsync Recipe Agent", "version": "2.0.0"})

@app.route("/agent", methods=["POST"])
def recipe_discovery_agent():
    """
    Main agent endpoint - accepts prompt and user_id, returns recipe data
    Backend-only service triggered by webhook from RecipeSearchPage frontend
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
            
        prompt = data.get('prompt', '')
        user_id = data.get('user_id', 'anonymous')
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        logger.info(f"Processing recipe request for user {user_id}: {prompt}")
        
        # Step 1: Extract intent using OpenAI
        intent = recipe_agent.extract_intent(prompt)
        
        # Step 2: Build search query from intent
        keywords = intent.get('keywords', [])
        if isinstance(keywords, list):
            search_query = ' '.join(keywords[:3])  # Use first 3 keywords
        else:
            search_query = prompt
            
        # Add diet/meal type to search if available
        if intent.get('diet_type'):
            search_query = f"{intent['diet_type']} {search_query}"
        if intent.get('meal_type'):
            search_query = f"{intent['meal_type']} {search_query}"
        
        logger.info(f"Search query: {search_query}")
        
        # Step 3: Search real recipe websites
        recipes = recipe_agent.search_real_recipes(search_query, max_results=10)
        
        if not recipes:
            return jsonify({
                "recipes": [],
                "message": "No recipes found for your request. Please try different search terms."
            })
        
        # Step 4: Return first 10 recipes (title, image, description only for frontend)
        response_recipes = []
        for recipe in recipes:
            if recipe and recipe.get('title'):
                response_recipes.append({
                    "title": recipe['title'],
                    "image_url": recipe.get('image_url'),
                    "description": recipe.get('description', ''),
                    "recipe_id": recipe.get('recipe_id', '')
                })
        
        logger.info(f"Successfully found {len(response_recipes)} recipes")
        
        # Note: In production, Step 5 would store full recipe data in Supabase
        # for later use by MealPlanner module
        
        return jsonify({
            "recipes": response_recipes,
            "message": f"Found {len(response_recipes)} recipes for '{prompt}'"
        })
        
    except Exception as e:
        logger.error(f"Error processing recipe request: {e}")
        return jsonify({"error": f"Failed to process recipe request: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
