# Kitchnsync Recipe Discovery Agent

AI-powered backend agent for recipe discovery and meal planning. This service accepts natural language prompts and returns structured recipe data from authentic cooking websites.

## API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status.

### Recipe Discovery
```bash
POST /agent
Content-Type: application/json

{
  "prompt": "quick keto dinner",
  "user_id": "user_123"
}
```

Returns up to 10 recipes with title, image, description, and recipe_id for frontend display.

## Example Usage

```bash
# Test the agent endpoint
curl -X POST http://localhost:5000/agent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "easy pasta recipe", "user_id": "test_user"}'
```

## Response Format

```json
{
  "recipes": [
    {
      "title": "Classic Spaghetti Carbonara",
      "image_url": "https://example.com/image.jpg",
      "description": "A traditional Italian pasta dish...",
      "recipe_id": "abc123"
    }
  ],
  "message": "Found 5 recipes for 'easy pasta recipe'"
}
```

## Features

- OpenAI GPT-4 intent extraction from natural language prompts
- Real-time recipe scraping from authentic cooking websites (AllRecipes, EatingWell, Food Network)
- Schema.org structured data extraction for reliable recipe parsing
- Fallback HTML parsing when structured data unavailable
- Backend-only service designed for webhook integration

## Architecture

The agent follows these steps:
1. Extract intent (meal type, diet type, keywords) using OpenAI
2. Query recipe sources (configurable via Supabase in production)
3. Filter out user's hated recipes (via Supabase in production)
4. Scrape and parse recipe pages using Schema.org JSON-LD
5. Return limited recipe data to frontend
6. Store full recipe data for MealPlanner module (Supabase integration ready)

## Environment Variables

```bash
OPENAI_API_KEY=your_openai_api_key
SESSION_SECRET=your_session_secret
```

## Running the Service

The service runs on Flask with Gunicorn for production compatibility:

```bash
python main.py
# Service available at http://localhost:5000
```

## Production Notes

- Ready for Supabase integration (recipe_sources and hated_recipes tables)
- Designed as webhook endpoint for RecipeSearchPage frontend
- Stores full recipe data for later use by MealPlanner module
- Rate limiting and caching recommended for production deployment