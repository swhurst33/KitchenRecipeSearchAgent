import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import extruct
from models import RecipeModel, IngredientModel, MacrosModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Supported recipe websites
        self.supported_domains = [
            'allrecipes.com',
            'eatingwell.com',
            'delish.com',
            'bbcgoodfood.com',
            'foodnetwork.com',
            'recipetineats.com',
            'tasteofhome.com'
        ]

    def search_recipes(self, search_queries: List[str], max_results: int = 5) -> List[str]:
        """Search for recipe URLs using Google search"""
        recipe_urls = []
        
        for query in search_queries[:2]:  # Limit to 2 queries to avoid rate limits
            try:
                # Create a focused search query for recipes
                search_query = f"{query} recipe site:allrecipes.com OR site:eatingwell.com OR site:delish.com OR site:bbcgoodfood.com"
                
                # Use a simple approach - construct URLs based on known patterns
                # This is a simplified approach for the MVP
                urls = self._generate_recipe_urls(query)
                recipe_urls.extend(urls)
                
                if len(recipe_urls) >= max_results:
                    break
                    
            except Exception as e:
                logger.error(f"Error searching for recipes with query '{query}': {e}")
                continue
        
        return recipe_urls[:max_results]

    def _generate_recipe_urls(self, query: str) -> List[str]:
        """Generate potential recipe URLs based on query patterns"""
        urls = []
        
        # Simple keyword-based URL generation for common recipe sites
        # This is a simplified approach - in production you'd use proper search APIs
        search_terms = query.lower().replace(' ', '-')
        
        base_urls = [
            f"https://www.allrecipes.com/search/results/?search={query.replace(' ', '+')}&page=1",
            f"https://www.eatingwell.com/search?q={query.replace(' ', '+')}"
        ]
        
        # Try to get actual recipe URLs from search pages
        for base_url in base_urls:
            try:
                response = self.session.get(base_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract recipe links from search results
                    recipe_links = []
                    
                    # AllRecipes pattern
                    if 'allrecipes.com' in base_url:
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if '/recipe/' in href and href.startswith('http'):
                                recipe_links.append(href)
                    
                    # EatingWell pattern
                    elif 'eatingwell.com' in base_url:
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if '/recipe/' in href:
                                if href.startswith('/'):
                                    href = 'https://www.eatingwell.com' + href
                                recipe_links.append(href)
                    
                    urls.extend(recipe_links[:3])  # Take first 3 from each source
                    
            except Exception as e:
                logger.error(f"Error fetching search results from {base_url}: {e}")
                continue
        
        # Fallback: generate some common recipe URLs if search fails
        if not urls:
            urls = self._fallback_recipe_urls(query)
        
        return urls[:5]

    def _fallback_recipe_urls(self, query: str) -> List[str]:
        """Fallback method to generate recipe URLs when search fails"""
        # This is a simplified fallback - generate URLs based on common patterns
        fallback_urls = []
        
        # Common recipe patterns for different sites
        query_slug = query.lower().replace(' ', '-').replace(',', '')
        
        patterns = [
            f"https://www.allrecipes.com/recipe/easy-{query_slug}",
            f"https://www.eatingwell.com/recipe/{query_slug}",
            f"https://www.delish.com/cooking/recipe-ideas/{query_slug}-recipe"
        ]
        
        return patterns

    def parse_recipe(self, url: str) -> Optional[RecipeModel]:
        """Parse a recipe from a given URL"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch recipe from {url}: Status {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try Schema.org JSON-LD first
            recipe_data = self._extract_jsonld_recipe(soup)
            if recipe_data:
                return self._create_recipe_model(recipe_data, url)
            
            # Fallback to CSS selector parsing
            recipe_data = self._extract_css_recipe(soup, url)
            if recipe_data:
                return self._create_recipe_model(recipe_data, url)
            
            logger.warning(f"Could not parse recipe from {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing recipe from {url}: {e}")
            return None

    def _extract_jsonld_recipe(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract recipe data from JSON-LD structured data"""
        try:
            # Find JSON-LD scripts
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Handle different JSON-LD structures
                    if isinstance(data, list):
                        for item in data:
                            if self._is_recipe_data(item):
                                return item
                    elif isinstance(data, dict):
                        if self._is_recipe_data(data):
                            return data
                        # Check for nested recipe data
                        if '@graph' in data:
                            for item in data['@graph']:
                                if self._is_recipe_data(item):
                                    return item
                                    
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON-LD recipe: {e}")
            return None

    def _is_recipe_data(self, data: Dict) -> bool:
        """Check if data contains recipe information"""
        if not isinstance(data, dict):
            return False
        
        type_field = data.get('@type', '')
        if isinstance(type_field, list):
            return 'Recipe' in type_field
        return type_field == 'Recipe'

    def _extract_css_recipe(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract recipe data using CSS selectors as fallback"""
        try:
            recipe_data = {}
            
            # Extract title
            title_selectors = [
                'h1.recipe-title',
                'h1[itemprop="name"]',
                '.recipe-header h1',
                '.entry-title',
                'h1'
            ]
            title = self._find_text_by_selectors(soup, title_selectors)
            if title:
                recipe_data['name'] = title
            
            # Extract image
            img_selectors = [
                'img[itemprop="image"]',
                '.recipe-image img',
                '.recipe-photo img',
                'img.recipe-img'
            ]
            image_url = self._find_image_by_selectors(soup, img_selectors, url)
            if image_url:
                recipe_data['image'] = image_url
            
            # Extract ingredients
            ingredient_selectors = [
                '[itemprop="recipeIngredient"]',
                '.recipe-ingredient',
                '.ingredients li',
                '.ingredient-item'
            ]
            ingredients = self._find_ingredients_by_selectors(soup, ingredient_selectors)
            if ingredients:
                recipe_data['recipeIngredient'] = ingredients
            
            # Extract instructions
            instruction_selectors = [
                '[itemprop="recipeInstructions"]',
                '.recipe-instruction',
                '.instructions li',
                '.method li',
                '.directions li'
            ]
            instructions = self._find_instructions_by_selectors(soup, instruction_selectors)
            if instructions:
                recipe_data['recipeInstructions'] = instructions
            
            return recipe_data if recipe_data else None
            
        except Exception as e:
            logger.error(f"Error extracting recipe with CSS selectors: {e}")
            return None

    def _find_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Find text content using multiple CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _find_image_by_selectors(self, soup: BeautifulSoup, selectors: List[str], base_url: str) -> Optional[str]:
        """Find image URL using multiple CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src') or element.get('data-src')
                if src:
                    return urljoin(base_url, src)
        return None

    def _find_ingredients_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find ingredients using multiple CSS selectors"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                return [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
        return []

    def _find_instructions_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find instructions using multiple CSS selectors"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                instructions = []
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10:  # Filter out very short instructions
                        instructions.append(text)
                if instructions:
                    return instructions
        return []

    def _create_recipe_model(self, recipe_data: Dict, url: str) -> RecipeModel:
        """Create a RecipeModel from parsed recipe data"""
        # Extract title
        title = recipe_data.get('name', 'Unknown Recipe')
        
        # Extract image URL
        image_url = None
        if 'image' in recipe_data:
            image = recipe_data['image']
            if isinstance(image, str):
                image_url = image
            elif isinstance(image, dict) and 'url' in image:
                image_url = image['url']
            elif isinstance(image, list) and len(image) > 0:
                first_image = image[0]
                if isinstance(first_image, str):
                    image_url = first_image
                elif isinstance(first_image, dict) and 'url' in first_image:
                    image_url = first_image['url']
        
        # Extract ingredients
        ingredients = []
        recipe_ingredients = recipe_data.get('recipeIngredient', [])
        for ingredient_text in recipe_ingredients:
            if isinstance(ingredient_text, str):
                # Try to parse quantity and unit
                quantity, unit = self._parse_ingredient_quantity(ingredient_text)
                ingredients.append(IngredientModel(
                    text=ingredient_text,
                    quantity=quantity,
                    unit=unit
                ))
        
        # Extract instructions
        instructions = []
        recipe_instructions = recipe_data.get('recipeInstructions', [])
        for instruction in recipe_instructions:
            if isinstance(instruction, str):
                instructions.append(instruction)
            elif isinstance(instruction, dict) and 'text' in instruction:
                instructions.append(instruction['text'])
        
        # Extract nutrition/macros
        macros = None
        nutrition = recipe_data.get('nutrition')
        if nutrition:
            macros = MacrosModel(
                calories=self._extract_numeric_value(nutrition.get('calories')),
                protein=self._extract_numeric_value(nutrition.get('proteinContent')),
                fat=self._extract_numeric_value(nutrition.get('fatContent')),
                carbs=self._extract_numeric_value(nutrition.get('carbohydrateContent'))
            )
        
        return RecipeModel(
            title=title,
            image_url=image_url,
            source_url=url,
            ingredients=ingredients,
            instructions=instructions,
            macros=macros
        )

    def _parse_ingredient_quantity(self, ingredient_text: str) -> tuple[Optional[float], Optional[str]]:
        """Parse quantity and unit from ingredient text"""
        try:
            # Simple regex to extract numbers and common units
            pattern = r'^(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*([a-zA-Z]+)?'
            match = re.match(pattern, ingredient_text.strip())
            
            if match:
                quantity_str = match.group(1)
                unit = match.group(2)
                
                # Handle fractions
                if '/' in quantity_str:
                    parts = quantity_str.split('/')
                    quantity = float(parts[0]) / float(parts[1])
                else:
                    quantity = float(quantity_str)
                
                return quantity, unit
            
        except (ValueError, AttributeError):
            pass
        
        return None, None

    def _extract_numeric_value(self, value) -> Optional[float]:
        """Extract numeric value from various formats"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove units and extract number
            numeric_str = re.sub(r'[^\d.]', '', value)
            try:
                return float(numeric_str) if numeric_str else None
            except ValueError:
                return None
        
        return None

    def get_recipes(self, search_queries: List[str], max_recipes: int = 5) -> List[RecipeModel]:
        """Main method to search and parse recipes"""
        recipe_urls = self.search_recipes(search_queries, max_recipes * 2)  # Get more URLs than needed
        recipes = []
        
        for url in recipe_urls:
            if len(recipes) >= max_recipes:
                break
                
            recipe = self.parse_recipe(url)
            if recipe:
                recipes.append(recipe)
                logger.info(f"Successfully parsed recipe: {recipe.title}")
            else:
                logger.warning(f"Failed to parse recipe from: {url}")
        
        return recipes
