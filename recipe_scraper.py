"""
Recipe scraper that finds and parses recipes from authentic sources
"""

import asyncio
import hashlib
import logging
import re
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
from models import FullRecipeModel, IngredientModel, NutritionModel, RecipeIntent
from supabase_sources import get_recipe_sources
from supabase_filters import filter_hated_recipes

logger = logging.getLogger(__name__)

class RecipeScraper:
    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        # Real recipe website search patterns
        self.search_patterns = {
            'allrecipes.com': 'https://www.allrecipes.com/search/results/?search={query}',
            'eatingwell.com': 'https://www.eatingwell.com/search?q={query}',
            'foodnetwork.com': 'https://www.foodnetwork.com/search/{query}',
            'tasteofhome.com': 'https://www.tasteofhome.com/search/?q={query}',
            'recipetineats.com': 'https://www.recipetineats.com/?s={query}',
            'simplyrecipes.com': 'https://www.simplyrecipes.com/search?q={query}'
        }

    async def find_recipes(self, keywords: List[str], meal_type: Optional[str], 
                          diet_type: Optional[str], user_id: str, max_recipes: int = 10) -> List[FullRecipeModel]:
        """
        Find recipes based on search criteria
        """
        try:
            # Get recipe sources from Supabase
            sources = await get_recipe_sources()
            
            # Build search queries
            search_queries = self._build_search_queries(keywords, meal_type, diet_type)
            
            # Find recipe URLs from multiple sources
            recipe_urls = []
            for query in search_queries[:3]:  # Limit to 3 queries
                for source in sources[:3]:  # Limit to 3 sources
                    urls = await self._search_recipes_on_site(query, source)
                    recipe_urls.extend(urls)
                    if len(recipe_urls) >= max_recipes * 2:  # Get more than needed for filtering
                        break
                if len(recipe_urls) >= max_recipes * 2:
                    break
            
            # Remove duplicates
            recipe_urls = list(dict.fromkeys(recipe_urls))
            
            # Parse recipes from URLs
            recipes = []
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
            
            tasks = []
            for url in recipe_urls[:max_recipes * 2]:
                task = self._parse_recipe_with_semaphore(semaphore, url)
                tasks.append(task)
            
            parsed_recipes = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            for recipe in parsed_recipes:
                if isinstance(recipe, FullRecipeModel):
                    recipes.append(recipe)
                if len(recipes) >= max_recipes:
                    break
            
            # Filter out hated recipes
            filtered_recipes = await filter_hated_recipes(recipes, user_id)
            
            return filtered_recipes[:max_recipes]
            
        except Exception as e:
            logger.error(f"Error finding recipes: {e}")
            return []

    async def _search_recipes_on_site(self, query: str, source_domain: str) -> List[str]:
        """
        Search for recipe URLs on a specific website
        """
        try:
            if source_domain not in self.search_patterns:
                return []
                
            search_url = self.search_patterns[source_domain].format(query=query.replace(' ', '+'))
            
            response = await self.session.get(search_url)
            if response.status_code != 200:
                logger.warning(f"Search failed for {source_domain}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            recipe_urls = []
            
            # Site-specific URL extraction patterns
            if 'allrecipes.com' in source_domain:
                links = soup.find_all('a', href=re.compile(r'/recipe/\d+'))
                for link in links[:10]:
                    if link.get('href'):
                        full_url = urljoin('https://www.allrecipes.com', link['href'])
                        recipe_urls.append(full_url)
                        
            elif 'eatingwell.com' in source_domain:
                links = soup.find_all('a', href=re.compile(r'/recipe/'))
                for link in links[:10]:
                    if link.get('href'):
                        full_url = urljoin('https://www.eatingwell.com', link['href'])
                        recipe_urls.append(full_url)
                        
            elif 'foodnetwork.com' in source_domain:
                links = soup.find_all('a', href=re.compile(r'/recipes/'))
                for link in links[:10]:
                    if link.get('href'):
                        full_url = urljoin('https://www.foodnetwork.com', link['href'])
                        recipe_urls.append(full_url)
                        
            elif 'simplyrecipes.com' in source_domain:
                links = soup.find_all('a', href=re.compile(r'\.com/.*-recipe'))
                for link in links[:10]:
                    if link.get('href'):
                        recipe_urls.append(link['href'])
            
            return recipe_urls[:10]
            
        except Exception as e:
            logger.error(f"Error searching {source_domain}: {e}")
            return []

    async def _parse_recipe_with_semaphore(self, semaphore: asyncio.Semaphore, url: str) -> Optional[FullRecipeModel]:
        """
        Parse a recipe with semaphore to limit concurrent requests
        """
        async with semaphore:
            return await self._parse_recipe(url)

    async def _parse_recipe(self, url: str) -> Optional[FullRecipeModel]:
        """
        Parse a single recipe from URL using Schema.org JSON-LD and fallback methods
        """
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch recipe from {url}: Status {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try Schema.org JSON-LD first
            recipe_data = self._extract_jsonld_recipe(soup)
            
            if not recipe_data:
                # Fallback to microdata and CSS selectors
                recipe_data = self._extract_fallback_recipe(soup, url)
            
            if not recipe_data:
                return None
                
            return self._create_recipe_model(recipe_data, url)
            
        except Exception as e:
            logger.error(f"Error parsing recipe from {url}: {e}")
            return None

    def _extract_jsonld_recipe(self, soup: BeautifulSoup) -> Optional[dict]:
        """
        Extract recipe data from Schema.org JSON-LD structured data
        """
        try:
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

    def _is_recipe_data(self, data: dict) -> bool:
        """
        Check if data contains recipe information
        """
        if not isinstance(data, dict):
            return False
        
        type_field = data.get('@type', '')
        if isinstance(type_field, list):
            return 'Recipe' in type_field
        return type_field == 'Recipe'

    def _extract_fallback_recipe(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """
        Extract recipe data using CSS selectors and microdata as fallback
        """
        try:
            recipe_data = {}
            
            # Extract title
            title_selectors = [
                'h1[itemprop="name"]',
                'h1.recipe-title',
                '.recipe-header h1',
                '.entry-title',
                'h1'
            ]
            title = self._find_text_by_selectors(soup, title_selectors)
            if title:
                recipe_data['name'] = title
            
            # Extract description
            desc_selectors = [
                '[itemprop="description"]',
                '.recipe-description',
                '.recipe-summary',
                'meta[name="description"]'
            ]
            description = self._find_text_by_selectors(soup, desc_selectors)
            if description:
                recipe_data['description'] = description
            
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
            logger.error(f"Error extracting recipe with fallback selectors: {e}")
            return None

    def _find_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Find text content using multiple CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Handle meta tags
                if element.name == 'meta':
                    return element.get('content', '').strip()
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

    def _create_recipe_model(self, recipe_data: dict, url: str) -> FullRecipeModel:
        """
        Create a FullRecipeModel from parsed recipe data
        """
        # Generate recipe ID from URL
        recipe_id = hashlib.md5(url.encode()).hexdigest()
        
        # Extract title
        title = recipe_data.get('name', 'Unknown Recipe')
        
        # Extract description
        description = recipe_data.get('description', '')
        if isinstance(description, dict):
            description = description.get('text', '')
        
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
        
        # Extract nutrition
        nutrition = None
        nutrition_data = recipe_data.get('nutrition')
        if nutrition_data:
            nutrition = NutritionModel(
                calories=self._extract_numeric_value(nutrition_data.get('calories')),
                protein=self._extract_numeric_value(nutrition_data.get('proteinContent')),
                fat=self._extract_numeric_value(nutrition_data.get('fatContent')),
                carbs=self._extract_numeric_value(nutrition_data.get('carbohydrateContent')),
                fiber=self._extract_numeric_value(nutrition_data.get('fiberContent')),
                sugar=self._extract_numeric_value(nutrition_data.get('sugarContent'))
            )
        
        return FullRecipeModel(
            recipe_id=recipe_id,
            title=title,
            description=description if description else None,
            image_url=image_url,
            source_url=url,
            ingredients=ingredients,
            instructions=instructions,
            nutrition=nutrition
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

    def _build_search_queries(self, keywords: List[str], meal_type: Optional[str], diet_type: Optional[str]) -> List[str]:
        """
        Build optimized search queries from extracted intent
        """
        queries = []
        
        # Base query from keywords
        if keywords:
            base_query = ' '.join(keywords[:3])  # Use first 3 keywords
            queries.append(base_query)
            
            # Add meal type if available
            if meal_type:
                queries.append(f"{meal_type} {base_query}")
                
            # Add diet type if available
            if diet_type:
                queries.append(f"{diet_type} {base_query}")
                
            # Combine meal and diet type
            if meal_type and diet_type:
                queries.append(f"{diet_type} {meal_type} {base_query}")
        
        # Fallback queries
        if not queries:
            queries = ["easy dinner recipe", "simple lunch recipe"]
        
        return queries[:5]  # Limit to 5 queries