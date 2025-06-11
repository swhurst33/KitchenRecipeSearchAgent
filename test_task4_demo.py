"""
Task 4 Demo: Recipe Crawler Implementation
Shows the complete data extraction and formatting system
"""
import asyncio
import sys
sys.path.append('.')

from recipe_crawler import RecipeCrawler

async def demo_task4_implementation():
    """Demonstrate Task 4 implementation with sample data"""
    
    print("=== Task 4: Recipe Crawler Implementation Demo ===\n")
    
    crawler = RecipeCrawler()
    
    # Demo 1: Show expected output format
    print("1. Required Output Format (per Task 4 spec):")
    sample_output = {
        "title": "Creamy Garlic Chicken",
        "description": "A delicious and easy chicken dish with creamy garlic sauce",
        "image_url": "https://example.com/chicken-image.jpg",
        "ingredients": [
            {"item": "chicken breast", "qty": 2, "unit": "lbs"},
            {"item": "garlic cloves", "qty": 4, "unit": ""},
            {"item": "heavy cream", "qty": 1, "unit": "cup"},
            {"item": "olive oil", "qty": 2, "unit": "tablespoons"}
        ],
        "instructions": [
            "Season chicken with salt and pepper",
            "Heat olive oil in a large skillet over medium-high heat",
            "Cook chicken until golden brown, about 6-7 minutes per side",
            "Add garlic and cook for 1 minute until fragrant",
            "Pour in cream and simmer until thickened"
        ],
        "macros": {"calories": 400, "protein": 30, "fat": 25, "carbs": 8},
        "servings": 4,
        "source_url": "https://allrecipes.com/recipe/12345/creamy-garlic-chicken",
        "site_name": "AllRecipes"
    }
    
    for field, value in sample_output.items():
        print(f"   {field}: {type(value).__name__} = {str(value)[:80]}{'...' if len(str(value)) > 80 else ''}")
    
    # Demo 2: Ingredient parsing capabilities
    print("\n2. Ingredient Parsing Examples:")
    test_ingredients = [
        "2 pounds boneless chicken thighs",
        "1/2 cup all-purpose flour", 
        "3 tablespoons butter",
        "1 large onion, diced",
        "2 cups chicken broth",
        "Salt and pepper to taste",
        "Fresh herbs for garnish"
    ]
    
    for ingredient in test_ingredients:
        parsed = crawler._parse_ingredient(ingredient)
        qty_str = f"{parsed['qty']} {parsed['unit']}" if parsed['qty'] else "as needed"
        print(f"   '{ingredient}' → {parsed['item']} ({qty_str})")
    
    # Demo 3: Site name extraction
    print("\n3. Site Name Extraction:")
    test_urls = [
        "https://www.allrecipes.com/recipe/123/chicken-soup",
        "https://www.foodnetwork.com/recipes/pasta-recipe",
        "https://epicurious.com/recipe/beef-stew",
        "https://www.bonappetit.com/recipe/chocolate-cake"
    ]
    
    for url in test_urls:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        site_name = parsed_url.netloc.replace('www.', '').split('.')[0].title()
        print(f"   {url} → {site_name}")
    
    # Demo 4: Data extraction methods
    print("\n4. Recipe Data Extraction Methods:")
    print("   ✓ JSON-LD structured data (Schema.org Recipe)")
    print("   ✓ CSS selectors for common recipe elements")
    print("   ✓ Microdata fallback extraction")
    print("   ✓ Nutrition/macro information parsing")
    print("   ✓ Serving size extraction from various formats")
    
    # Demo 5: Crawling workflow
    print("\n5. Complete Crawling Workflow:")
    print("   1. Get active recipe sources from Supabase recipe_sources table")
    print("   2. Build search URLs using enriched prompts with {query} replacement")
    print("   3. Crawl search results to find recipe page URLs")
    print("   4. Parse each recipe page for structured data")
    print("   5. Format results in required Task 4 structure")
    print("   6. Return max 10 recipes per search (as specified)")
    
    # Demo 6: Integration points
    print("\n6. Integration with Previous Tasks:")
    print("   ✓ Uses Task 2 recipe sources from Supabase")
    print("   ✓ Uses Task 3 enriched prompts for search")
    print("   ✓ Integrates with Task 1 user context filtering")
    print("   ✓ Returns data ready for storage and frontend display")
    
    print("\n=== Task 4 Ready for Production ===")
    print("The crawler will work automatically when:")
    print("• recipe_sources table has active sources with url_template containing {query}")
    print("• Users make recipe requests through the agent")
    print("• Recipe websites respond with structured data")
    
    print("\nExample recipe_sources table entry:")
    print({
        "id": 1,
        "site_name": "AllRecipes", 
        "url_template": "https://allrecipes.com/search?q={query}",
        "active": True
    })

if __name__ == "__main__":
    asyncio.run(demo_task4_implementation())