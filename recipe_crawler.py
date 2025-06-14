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
    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        )

    async def crawl_and_scrape_recipes(self, enriched_prompt: str, disliked_ingredients: List[str], max_recipes: int = 10) -> List[Dict[str, Any]]:
        try:
            sources = await get_active_recipe_sources()
            if not sources:
                logger.warning("No active recipe sources found")
                return []

            search_urls = build_search_urls(enriched_prompt, sources)
            if not search_urls:
                logger.warning("No search URLs generated")
                return []

            logger.info(f"Generated {len(search_urls)} search URLs for crawling")
            recipes_by_site = {}

            for search_url in search_urls:
                urls = await self._find_recipe_urls_from_search(search_url)
                parsed_site = urlparse(search_url).netloc.replace("www.", "").split(".")[0].lower()

                for url in urls:
                    recipe = await self._scrape_recipe(url)
                    if (
                        recipe
                        and recipe["ingredients"]
                        and recipe["instructions"]
                        and not self._contains_disliked_ingredients(recipe["ingredients"], disliked_ingredients)
                        and parsed_site not in recipes_by_site
                    ):
                        recipes_by_site[parsed_site] = recipe
                        break

            recipes = list(recipes_by_site.values())[:max_recipes]
            logger.info(f"Successfully scraped {len(recipes)} recipes")
            return recipes

        except Exception as e:
            logger.error(f"Error in crawl_and_scrape_recipes: {e}")
            return []

    def _contains_disliked_ingredients(self, ingredients: List[str], dislikes: List[str]) -> bool:
        for ing in ingredients:
            for dis in dislikes:
                if dis.lower() in ing.lower():
                    return True
        return False

    async def _find_recipe_urls_from_search(self, search_url: str) -> List[str]:
        try:
            response = await self.session.get(search_url)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, "html.parser")
            recipe_urls = []

            selectors = [
                'a[href*="/recipe/"]', 'a[href*="/recipes/"]', 'a[href*="recipe-"]',
                'a[href*="-recipe"]', ".recipe-card a", ".recipe-item a", ".recipe-link",
                "article a", ".card a",
            ]

            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get("href")
                    if href:
                        full_url = urljoin(search_url, href)
                        if self._is_recipe_url(full_url):
                            recipe_urls.append(full_url)

            all_links = soup.find_all("a", href=True)
            for link in all_links[:50]:
                href = link.get("href")
                if href:
                    full_url = urljoin(search_url, href)
                    if self._is_recipe_url(full_url):
                        recipe_urls.append(full_url)

            unique_urls = list(dict.fromkeys(recipe_urls))
            logger.info(f"Found {len(unique_urls)} recipe URLs from {search_url}")
            return unique_urls[:20]

        except Exception as e:
            logger.error(f"Error finding recipe URLs from {search_url}: {e}")
            return []

    def _is_recipe_url(self, url: str) -> bool:
        url_lower = url.lower()
        excluded_keywords = ["/topics/", "/collections/", "/category/", "/tags/", "/videos/", "/guides/", "/about/", "/how-to/", "/contact/"]
        if any(exclude in url_lower for exclude in excluded_keywords):
            return False

        recipe_indicators = ["/recipe/", "/recipes/", "recipe-", "-recipe", "/meal/", "/dinner/", "/lunch/", "/breakfast/"]
        return any(indicator in url_lower for indicator in recipe_indicators)

    async def _scrape_recipe(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")
            recipe_data = self._extract_jsonld_recipe(soup)
            if not recipe_data:
                recipe_data = self._extract_fallback_recipe(soup)
            if not recipe_data:
                return None

            return self._format_recipe_output(recipe_data, url)

        except Exception as e:
            logger.error(f"Error scraping recipe from {url}: {e}")
            return None

    def _extract_jsonld_recipe(self, soup: BeautifulSoup) -> Optional[Dict]:
        try:
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            for item in data:
                                if self._is_recipe_data(item):
                                    return item
                        elif isinstance(data, dict):
                            if self._is_recipe_data(data):
                                return data
                            for value in data.values():
                                if isinstance(value, dict) and self._is_recipe_data(value):
                                    return value
                                elif isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and self._is_recipe_data(item):
                                            return item
                    except (json.JSONDecodeError, TypeError):
                        continue
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON-LD: {e}")
            return None

    def _is_recipe_data(self, data: Dict) -> bool:
        if not isinstance(data, dict):
            return False
        type_field = data.get("@type")
        if isinstance(type_field, list):
            return any(isinstance(t, str) and "recipe" in t.lower() for t in type_field)
        elif isinstance(type_field, str):
            return "recipe" in type_field.lower()
        recipe_fields = ["name", "recipeIngredient", "recipeInstructions"]
        return any(field in data for field in recipe_fields)

    def _extract_fallback_recipe(self, soup: BeautifulSoup) -> Optional[Dict]:
        return None

    def _parse_servings(self, value: Any) -> Optional[int]:
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                match = re.search(r"\\d+", value)
                if match:
                    return int(match.group())
            return None
        except Exception as e:
            logger.warning(f"Error parsing servings from {value}: {e}")
            return None

    def _format_recipe_output(self, data: Dict, url: str) -> Dict[str, Any]:
        image_url = data.get("image")
        if isinstance(image_url, dict):
            image_url = image_url.get("url", "")
        elif isinstance(image_url, list):
            image_url = image_url[0] if image_url else ""

        ingredients = data.get("recipeIngredient", [])
        if not isinstance(ingredients, list):
            ingredients = [ingredients]

        instructions = data.get("recipeInstructions", [])
        if isinstance(instructions, list):
            cleaned_instructions = []
            for step in instructions:
                if isinstance(step, str):
                    cleaned_instructions.append(step.strip())
                elif isinstance(step, dict):
                    cleaned_instructions.append(step.get("text", "").strip())
            instructions = cleaned_instructions
        elif isinstance(instructions, str):
            instructions = [instructions.strip()]
        else:
            instructions = []

        return {
            "title": data.get("name", ""),
            "description": data.get("description", ""),
            "image_url": image_url,
            "ingredients": ingredients,
            "instructions": instructions,
            "macros": {},
            "servings": self._parse_servings(data.get("recipeYield")),
            "source_url": url,
            "site_name": urlparse(url).netloc,
        }
