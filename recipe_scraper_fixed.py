"""
Recipe scraper that finds and parses recipes from authentic sources using Supabase integration
"""

import asyncio
import logging
import re
from typing import List, Optional, Dict
import httpx
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
from models import FullRecipeModel, IngredientModel, NutritionModel, RecipeIntent
from supabase_sources import get_active_recipe_sources, build_search_urls
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

    async def find_recipes(self, keywords: List[str], meal_type: Optional[str], 
                          diet_type: Optional[str], user_id: str, max_recipes: int = 10) -> List[FullRecipeModel]:
        """
        Find recipes based on search criteria using dynamic Supabase sources
        """
        try:
            # Get active recipe sources from Supabase
            sources = await get_active_recipe_sources()
            
            if not sources:
                logger.warning("No active recipe sources found in Supabase")
                return []
            
            # Build search queries
            search_queries = self._build_search_queries(keywords, meal_type, diet_type)
            
            # Find recipe URLs from multiple sources using Supabase data
            recipe_urls = []
            for query in search_queries[:3]:  # Limit to 3 queries
                # Build search URLs using Supabase source templates
                search_urls = build_search_urls(query, sources)
                
                for search_url in search_urls[:5]:  # Limit to 5 search URLs per query
                    urls = await self._search_recipes_on_url(search_url)
                    recipe_urls.extend(urls)
                    if len(recipe_urls) >= max_recipes * 2:  # Get more than needed for filtering
                        break
                if len(recipe_urls) >= max_recipes * 2:
                    break
            
            # Remove duplicates
            recipe_urls = list(dict.fromkeys(recipe_urls))
            
            # Parse recipes with limited concurrency
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
            tasks = [
                self._parse_recipe_with_semaphore(semaphore, url)
                for url in recipe_urls[:max_recipes * 2]
            ]
            
            parsed_recipes = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful parses
            recipes = [
                recipe for recipe in parsed_recipes
                if isinstance(recipe, FullRecipeModel) and recipe is not None
            ]
            
            # Filter out hated recipes
            filtered_recipes = await filter_hated_recipes(recipes, user_id)
            
            logger.info(f"Found {len(filtered_recipes)} recipes after filtering")
            
            return filtered_recipes[:max_recipes]
            
        except Exception as e:
            logger.error(f"Error finding recipes: {e}")
            return []

    async def _search_recipes_on_url(self, search_url: str) -> List[str]:
        """
        Search for recipe URLs from a given search URL
        """
        try:
            response = await self.session.get(search_url)
            if response.status_code != 200:
                logger.warning(f"Search failed for {search_url}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            recipe_urls = []
            
            # Common selectors for recipe links across different websites
            link_selectors = [
                'a[href*="/recipe"]',
                'a[href*="/recipes"]',
                'a[href*="recipe-"]',
                '.recipe-link a',
                '.recipe-card a',
                '.recipe-title a',
                '[data-recipe] a',
                'article a'
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links:
                    if hasattr(link, 'get') and link.get('href'):
                        href = link['href']
                        full_url = urljoin(search_url, href)
                        if self._is_recipe_url(full_url):
                            recipe_urls.append(full_url)
                
                if len(recipe_urls) >= 10:  # Limit per search page
                    break
            
            return recipe_urls[:10]
            
        except Exception as e:
            logger.error(f"Error searching recipes on {search_url}: {e}")
            return []
    
    def _is_recipe_url(self, url: str) -> bool:
        """Check if URL looks like a recipe page"""
        url_lower = url.lower()
        recipe_indicators = [
            '/recipe/',
            '/recipes/',
            'recipe-',
            '-recipe',
            '/dish/',
            '/cooking/'
        ]
        return any(indicator in url_lower for indicator in recipe_indicators)

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
                    if script.string:
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
                    
        except Exception as e:
            logger.error(f"Error extracting JSON-LD: {e}")
        
        return None

    def _is_recipe_data(self, data: dict) -> bool:
        """
        Check if data contains recipe information
        """
        if not isinstance(data, dict):
            return False
            
        recipe_types = ['Recipe', 'recipe', 'http://schema.org/Recipe']
        data_type = data.get('@type', data.get('type', ''))
        
        if isinstance(data_type, str):
            return data_type in recipe_types
        elif isinstance(data_type, list):
            return any(t in recipe_types for t in data_type)
        
        return False

    def _extract_fallback_recipe(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """
        Extract recipe data using CSS selectors and microdata as fallback
        """
        try:
            recipe_data = {}
            
            # Extract title
            title = self._find_text_by_selectors(soup, [
                'h1.recipe-title',
                'h1[itemprop="name"]',
                '.recipe-header h1',
                '.entry-title',
                'h1'
            ])
            if title:
                recipe_data['name'] = title.strip()
            
            # Extract description
            description = self._find_text_by_selectors(soup, [
                '.recipe-description',
                '[itemprop="description"]',
                '.recipe-summary',
                '.entry-summary p'
            ])
            if description:
                recipe_data['description'] = description.strip()
            
            # Extract image
            image_url = self._find_image_by_selectors(soup, [
                '.recipe-image img',
                '[itemprop="image"]',
                '.wp-post-image',
                '.entry-content img'
            ], url)
            if image_url:
                recipe_data['image'] = image_url
            
            # Extract ingredients
            ingredients = self._find_ingredients_by_selectors(soup, [
                '[itemprop="recipeIngredient"]',
                '.recipe-ingredient',
                '.ingredients li',
                '.recipe-ingredients li'
            ])
            if ingredients:
                recipe_data['recipeIngredient'] = ingredients
            
            # Extract instructions
            instructions = self._find_instructions_by_selectors(soup, [
                '[itemprop="recipeInstructions"]',
                '.recipe-instruction',
                '.instructions li',
                '.recipe-instructions li',
                '.directions li'
            ])
            if instructions:
                recipe_data['recipeInstructions'] = instructions
            
            return recipe_data if recipe_data else None
            
        except Exception as e:
            logger.error(f"Error in fallback extraction: {e}")
            return None

    def _find_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Find text content using multiple CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                if text and text.strip():
                    return text.strip()
        return None

    def _find_image_by_selectors(self, soup: BeautifulSoup, selectors: List[str], base_url: str) -> Optional[str]:
        """Find image URL using multiple CSS selectors"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src') or element.get('data-src')
                if src:
                    return urljoin(base_url, str(src))
        return None

    def _find_ingredients_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find ingredients using multiple CSS selectors"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                ingredients = []
                for elem in elements:
                    text = elem.get_text()
                    if text and text.strip():
                        ingredients.append(text.strip())
                if ingredients:
                    return ingredients
        return []

    def _find_instructions_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find instructions using multiple CSS selectors"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                instructions = []
                for elem in elements:
                    text = elem.get_text()
                    if text and text.strip():
                        instructions.append(text.strip())
                if instructions:
                    return instructions
        return []

    def _create_recipe_model(self, recipe_data: dict, url: str) -> FullRecipeModel:
        """
        Create a FullRecipeModel from parsed recipe data
        """
        # Extract basic info
        title = recipe_data.get('name', 'Unknown Recipe')
        description = recipe_data.get('description', '')
        
        # Extract image
        image_data = recipe_data.get('image', '')
        image_url = None
        if isinstance(image_data, str):
            image_url = image_data
        elif isinstance(image_data, list) and image_data:
            image_url = image_data[0] if isinstance(image_data[0], str) else image_data[0].get('url', '')
        elif isinstance(image_data, dict):
            image_url = image_data.get('url', '')
        
        # Parse ingredients
        ingredients_data = recipe_data.get('recipeIngredient', [])
        ingredients = []
        for ingredient_text in ingredients_data:
            if isinstance(ingredient_text, str):
                quantity, unit = self._parse_ingredient_quantity(ingredient_text)
                ingredients.append(IngredientModel(
                    text=ingredient_text,
                    quantity=quantity,
                    unit=unit
                ))
        
        # Parse instructions
        instructions_data = recipe_data.get('recipeInstructions', [])
        instructions = []
        for instruction in instructions_data:
            if isinstance(instruction, str):
                instructions.append(instruction)
            elif isinstance(instruction, dict):
                text = instruction.get('text', '')
                if text:
                    instructions.append(text)
        
        # Parse nutrition
        nutrition_data = recipe_data.get('nutrition', {})
        nutrition = None
        if nutrition_data:
            nutrition = NutritionModel(
                calories=self._extract_numeric_value(nutrition_data.get('calories')),
                protein=self._extract_numeric_value(nutrition_data.get('proteinContent')),
                fat=self._extract_numeric_value(nutrition_data.get('fatContent')),
                carbs=self._extract_numeric_value(nutrition_data.get('carbohydrateContent')),
                fiber=self._extract_numeric_value(nutrition_data.get('fiberContent')),
                sugar=self._extract_numeric_value(nutrition_data.get('sugarContent'))
            )
        
        # Parse times and servings
        prep_time = self._extract_numeric_value(recipe_data.get('prepTime'))
        cook_time = self._extract_numeric_value(recipe_data.get('cookTime'))
        servings = self._extract_numeric_value(recipe_data.get('recipeYield'))
        
        # Generate recipe ID
        recipe_id = str(hash(url))[-8:]
        
        return FullRecipeModel(
            recipe_id=recipe_id,
            title=title,
            description=description,
            image_url=image_url,
            source_url=url,
            ingredients=ingredients,
            instructions=instructions,
            nutrition=nutrition,
            prep_time=prep_time,
            cook_time=cook_time,
            servings=servings,
            difficulty=recipe_data.get('difficulty'),
            cuisine_type=recipe_data.get('recipeCuisine'),
            meal_type=recipe_data.get('recipeCategory'),
            diet_tags=[]
        )

    def _parse_ingredient_quantity(self, ingredient_text: str) -> tuple[Optional[float], Optional[str]]:
        """Parse quantity and unit from ingredient text"""
        # Simple regex patterns for common quantities
        patterns = [
            r'^(\d+\.?\d*)\s*(\w+)',  # "2 cups", "1.5 tsp"
            r'^(\d+/\d+)\s*(\w+)',    # "1/2 cup"
            r'^(\d+)\s*(\w+)'         # "3 eggs"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, ingredient_text.strip())
            if match:
                quantity_str, unit = match.groups()
                try:
                    if '/' in quantity_str:
                        num, denom = quantity_str.split('/')
                        quantity = float(num) / float(denom)
                    else:
                        quantity = float(quantity_str)
                    return quantity, unit
                except ValueError:
                    continue
        
        return None, None

    def _extract_numeric_value(self, value) -> Optional[float]:
        """Extract numeric value from various formats"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Extract first number from string
            match = re.search(r'(\d+\.?\d*)', value)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        return None

    def _build_search_queries(self, keywords: List[str], meal_type: Optional[str], diet_type: Optional[str]) -> List[str]:
        """
        Build optimized search queries from extracted intent
        """
        queries = []
        
        # Base query with keywords
        base_query = ' '.join(keywords)
        queries.append(base_query)
        
        # Add meal type if specified
        if meal_type:
            queries.append(f"{base_query} {meal_type}")
        
        # Add diet type if specified
        if diet_type:
            queries.append(f"{base_query} {diet_type}")
            if meal_type:
                queries.append(f"{base_query} {meal_type} {diet_type}")
        
        return queries[:3]  # Limit to 3 queries