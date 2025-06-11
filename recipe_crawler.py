"""
Task 4: Recipe Crawler and Scraper
Crawls pages and extracts recipe data in the specified format
"""

import asyncio
import logging
import re
import json
from typing import List, Dict, Optional, Any
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from supabase_sources import get_active_recipe_sources, build_search_urls

logger = logging.getLogger(__name__)

class RecipeCrawler:
    """Crawls recipe pages and extracts structured data"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        )
    
    async def crawl_and_scrape_recipes(self, enriched_prompt: str, max_recipes: int = 10) -> List[Dict[str, Any]]:
        """
        Main method for Task 4: Crawl pages and scrape recipes
        
        Args:
            enriched_prompt: Enhanced prompt with user context
            max_recipes: Maximum recipes to return (default 10)
            
        Returns:
            List of recipe dictionaries with required structure
        """
        try:
            # Step 1: Get active recipe sources from Supabase
            sources = await get_active_recipe_sources()
            
            if not sources:
                logger.warning("No active recipe sources found")
                return []
            
            # Step 2: Build search URLs using enriched prompt
            search_urls = build_search_urls(enriched_prompt, sources)
            
            if not search_urls:
                logger.warning("No search URLs generated")
                return []
            
            logger.info(f"Generated {len(search_urls)} search URLs for crawling")
            
            # Step 3: Find recipe page URLs from search results
            recipe_urls = []
            for search_url in search_urls[:5]:  # Limit search URLs
                urls = await self._find_recipe_urls_from_search(search_url)
                recipe_urls.extend(urls)
                if len(recipe_urls) >= max_recipes * 2:  # Get extra for filtering
                    break
            
            # Remove duplicates
            recipe_urls = list(dict.fromkeys(recipe_urls))
            logger.info(f"Found {len(recipe_urls)} recipe URLs to crawl")
            
            # Step 4: Crawl and parse recipes with concurrency control
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
            tasks = [
                self._scrape_recipe_with_semaphore(semaphore, url)
                for url in recipe_urls[:max_recipes * 2]
            ]
            
            scraped_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Step 5: Filter successful results and format output
            recipes = []
            for result in scraped_results:
                if isinstance(result, dict) and result is not None:
                    recipes.append(result)
                    if len(recipes) >= max_recipes:
                        break
            
            logger.info(f"Successfully scraped {len(recipes)} recipes")
            return recipes[:max_recipes]
            
        except Exception as e:
            logger.error(f"Error in crawl_and_scrape_recipes: {e}")
            return []
    
    async def _find_recipe_urls_from_search(self, search_url: str) -> List[str]:
        """Find recipe URLs from search results page"""
        try:
            response = await self.session.get(search_url)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract URLs from search results
            recipe_urls = []
            
            # Common selectors for recipe links
            selectors = [
                'a[href*="/recipe/"]',
                'a[href*="/recipes/"]',
                'a[href*="recipe-"]',
                'a[href*="-recipe"]',
                '.recipe-card a',
                '.recipe-item a',
                '.recipe-link',
                'article a',
                '.card a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(search_url, href)
                        if self._is_recipe_url(full_url):
                            recipe_urls.append(full_url)
            
            # Also check general links that might be recipes
            all_links = soup.find_all('a', href=True)
            for link in all_links[:50]:  # Limit to first 50 links
                href = link.get('href')
                if href:
                    full_url = urljoin(search_url, href)
                    if self._is_recipe_url(full_url):
                        recipe_urls.append(full_url)
            
            # Remove duplicates and limit results
            unique_urls = list(dict.fromkeys(recipe_urls))
            logger.info(f"Found {len(unique_urls)} recipe URLs from {search_url}")
            
            return unique_urls[:20]  # Limit per search URL
            
        except Exception as e:
            logger.error(f"Error finding recipe URLs from {search_url}: {e}")
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
            '/cooking/',
            '/meal/',
            '/food/'
        ]
        return any(indicator in url_lower for indicator in recipe_indicators)
    
    async def _scrape_recipe_with_semaphore(self, semaphore: asyncio.Semaphore, url: str) -> Optional[Dict[str, Any]]:
        """Scrape recipe with concurrency control"""
        async with semaphore:
            return await self._scrape_recipe(url)
    
    async def _scrape_recipe(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single recipe and return in required format
        
        Returns:
            Dictionary with structure:
            {
                "title": "Creamy Garlic Chicken",
                "description": "...",
                "image_url": "...",
                "ingredients": [{"item": "chicken breast", "qty": 2, "unit": "lbs"}],
                "instructions": ["Step 1...", "Step 2..."],
                "macros": {"calories": 400, "protein": 30, ...},
                "servings": 4,
                "source_url": "https://...",
                "site_name": "AllRecipes"
            }
        """
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try JSON-LD structured data first
            recipe_data = self._extract_jsonld_recipe(soup)
            
            if not recipe_data:
                # Fallback to microdata and CSS selectors
                recipe_data = self._extract_fallback_recipe(soup)
            
            if not recipe_data:
                return None
            
            # Format according to Task 4 requirements
            formatted_recipe = self._format_recipe_output(recipe_data, url)
            
            if formatted_recipe and formatted_recipe.get('title'):
                logger.info(f"Successfully scraped: {formatted_recipe['title']}")
                return formatted_recipe
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping recipe from {url}: {e}")
            return None
    
    def _extract_jsonld_recipe(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract recipe from JSON-LD structured data"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                if script.string:
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
                            # Check nested structures
                            for key, value in data.items():
                                if isinstance(value, dict) and self._is_recipe_data(value):
                                    return value
                                elif isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and self._is_recipe_data(item):
                                            return item
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON-LD: {e}")
            return None
    
    def _is_recipe_data(self, data: Dict) -> bool:
        """Check if data contains recipe information"""
        if not isinstance(data, dict):
            return False
        
        type_field = data.get('@type', '').lower()
        if 'recipe' in type_field:
            return True
        
        # Check for recipe-like fields
        recipe_fields = ['name', 'recipeIngredient', 'recipeInstructions']
        return any(field in data for field in recipe_fields)
    
    def _extract_fallback_recipe(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract recipe using CSS selectors and microdata as fallback"""
        try:
            recipe_data = {}
            
            # Title
            title = self._find_text_by_selectors(soup, [
                'h1.recipe-title',
                'h1.recipe-name',
                'h1[class*="title"]',
                'h1[class*="recipe"]',
                '.recipe-header h1',
                'h1',
                'title'
            ])
            if title:
                recipe_data['name'] = title
            
            # Description
            description = self._find_text_by_selectors(soup, [
                '.recipe-description',
                '.recipe-summary',
                '.recipe-intro',
                '[class*="description"]',
                'meta[name="description"]'
            ])
            if description:
                recipe_data['description'] = description
            
            # Image
            image = self._find_image_by_selectors(soup, [
                '.recipe-image img',
                '.recipe-photo img',
                'img[class*="recipe"]',
                '.hero-image img',
                'img[src*="recipe"]'
            ])
            if image:
                recipe_data['image'] = image
            
            # Ingredients
            ingredients = self._find_ingredients_by_selectors(soup, [
                '.recipe-ingredient',
                '.ingredient',
                '[class*="ingredient"]',
                'li[class*="ingredient"]',
                '.recipe-ingredients li'
            ])
            if ingredients:
                recipe_data['recipeIngredient'] = ingredients
            
            # Instructions
            instructions = self._find_instructions_by_selectors(soup, [
                '.recipe-instruction',
                '.instruction',
                '[class*="instruction"]',
                '.recipe-directions li',
                '.recipe-method li'
            ])
            if instructions:
                recipe_data['recipeInstructions'] = instructions
            
            # Servings
            servings = self._find_text_by_selectors(soup, [
                '.recipe-servings',
                '.servings',
                '[class*="serving"]',
                '.recipe-yield'
            ])
            if servings:
                recipe_data['recipeYield'] = servings
            
            return recipe_data if recipe_data else None
            
        except Exception as e:
            logger.error(f"Error in fallback extraction: {e}")
            return None
    
    def _find_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Find text content using multiple CSS selectors"""
        for selector in selectors:
            try:
                if selector.startswith('meta'):
                    element = soup.select_one(selector)
                    if element:
                        return element.get('content', '').strip()
                else:
                    element = soup.select_one(selector)
                    if element and element.get_text():
                        return element.get_text().strip()
            except:
                continue
        return None
    
    def _find_image_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Find image URL using multiple CSS selectors"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    src = element.get('src') or element.get('data-src')
                    if src:
                        return src.strip()
            except:
                continue
        return None
    
    def _find_ingredients_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find ingredients using multiple CSS selectors"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    ingredients = []
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 2:
                            ingredients.append(text)
                    if ingredients:
                        return ingredients
            except:
                continue
        return []
    
    def _find_instructions_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> List[str]:
        """Find instructions using multiple CSS selectors"""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    instructions = []
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 5:
                            instructions.append(text)
                    if instructions:
                        return instructions
            except:
                continue
        return []
    
    def _format_recipe_output(self, recipe_data: Dict, source_url: str) -> Dict[str, Any]:
        """
        Format recipe data according to Task 4 requirements
        
        Required structure:
        {
            "title": "Creamy Garlic Chicken",
            "description": "...",
            "image_url": "...",
            "ingredients": [{"item": "chicken breast", "qty": 2, "unit": "lbs"}],
            "instructions": ["Step 1...", "Step 2..."],
            "macros": {"calories": 400, "protein": 30, ...},
            "servings": 4,
            "source_url": "https://...",
            "site_name": "AllRecipes"
        }
        """
        try:
            # Extract site name from URL
            parsed_url = urlparse(source_url)
            site_name = parsed_url.netloc.replace('www.', '').split('.')[0].title()
            
            # Format ingredients as structured objects
            ingredients = []
            raw_ingredients = recipe_data.get('recipeIngredient', [])
            
            for ingredient in raw_ingredients:
                if isinstance(ingredient, str):
                    parsed = self._parse_ingredient(ingredient)
                    ingredients.append(parsed)
                elif isinstance(ingredient, dict):
                    ingredients.append(ingredient)
            
            # Format instructions as string list
            instructions = []
            raw_instructions = recipe_data.get('recipeInstructions', [])
            
            for instruction in raw_instructions:
                if isinstance(instruction, str):
                    instructions.append(instruction.strip())
                elif isinstance(instruction, dict):
                    text = instruction.get('text', '') or instruction.get('name', '')
                    if text:
                        instructions.append(text.strip())
            
            # Extract macros/nutrition
            macros = {}
            nutrition = recipe_data.get('nutrition', {})
            if isinstance(nutrition, dict):
                # Map common nutrition fields
                nutrition_mapping = {
                    'calories': ['calories', 'energyValue'],
                    'protein': ['proteinContent', 'protein'],
                    'fat': ['fatContent', 'fat'],
                    'carbs': ['carbohydrateContent', 'carbohydrates'],
                    'fiber': ['fiberContent', 'fiber'],
                    'sugar': ['sugarContent', 'sugar']
                }
                
                for macro_key, possible_fields in nutrition_mapping.items():
                    for field in possible_fields:
                        if field in nutrition:
                            value = nutrition[field]
                            if isinstance(value, str):
                                # Extract numeric value from strings like "400 calories"
                                numeric = re.search(r'(\d+)', value)
                                if numeric:
                                    macros[macro_key] = int(numeric.group(1))
                            elif isinstance(value, (int, float)):
                                macros[macro_key] = int(value)
                            break
            
            # Extract servings
            servings = recipe_data.get('recipeYield') or recipe_data.get('yield')
            if isinstance(servings, str):
                # Extract number from strings like "Serves 4" or "4 servings"
                numeric = re.search(r'(\d+)', servings)
                servings = int(numeric.group(1)) if numeric else None
            elif isinstance(servings, list) and servings:
                servings = servings[0]
                if isinstance(servings, str):
                    numeric = re.search(r'(\d+)', servings)
                    servings = int(numeric.group(1)) if numeric else None
            
            # Build final recipe dictionary
            formatted_recipe = {
                "title": recipe_data.get('name', '').strip(),
                "description": recipe_data.get('description', '').strip(),
                "image_url": recipe_data.get('image', '').strip(),
                "ingredients": ingredients,
                "instructions": instructions,
                "macros": macros,
                "servings": servings,
                "source_url": source_url,
                "site_name": site_name
            }
            
            return formatted_recipe
            
        except Exception as e:
            logger.error(f"Error formatting recipe output: {e}")
            return None
    
    def _parse_ingredient(self, ingredient_text: str) -> Dict[str, Any]:
        """Parse ingredient text into structured format"""
        try:
            # Simple parsing - extract quantity, unit, and item
            ingredient_text = ingredient_text.strip()
            
            # Pattern to match quantity and unit at the beginning
            pattern = r'^(\d+(?:\.\d+)?(?:/\d+)?)\s*([a-zA-Z]+)?\s+(.+)'
            match = re.match(pattern, ingredient_text)
            
            if match:
                qty_str, unit, item = match.groups()
                
                # Parse quantity (handle fractions)
                if '/' in qty_str:
                    parts = qty_str.split('/')
                    qty = float(parts[0]) / float(parts[1]) if len(parts) == 2 else float(parts[0])
                else:
                    qty = float(qty_str)
                
                return {
                    "item": item.strip(),
                    "qty": qty,
                    "unit": unit.strip() if unit else ""
                }
            else:
                # No quantity found, return as item only
                return {
                    "item": ingredient_text,
                    "qty": None,
                    "unit": ""
                }
                
        except Exception:
            # Fallback: return as item only
            return {
                "item": ingredient_text,
                "qty": None,
                "unit": ""
            }