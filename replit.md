# Kitchnsync Recipe Discovery Agent

## Overview

The Kitchnsync Recipe Discovery Agent is an AI-powered backend service that accepts natural language recipe prompts and returns structured recipe data from authentic cooking websites. This FastAPI-based application is designed to be triggered by webhook from a frontend RecipeSearchPage component and provides intelligent recipe discovery with user personalization.

## System Architecture

### Backend Framework
- **FastAPI**: Main application framework providing async API endpoints
- **Gunicorn**: WSGI server for production deployment with autoscale support
- **ASGI/WSGI Compatibility**: Custom adapter for seamless deployment

### AI and NLP Layer
- **OpenAI GPT-4**: Primary AI model for intent extraction and keyword optimization
- **Prompt Enrichment**: Context-aware prompt enhancement using user preferences
- **Keyword Extraction**: Optimized search terms for recipe discovery

### Data Storage
- **Supabase**: Primary database with PostgreSQL backend
- **Service Role Integration**: Bypasses Row Level Security for system operations
- **Multiple Tables**:
  - `recipe_search`: Bulk recipe storage with user association
  - `recipe_sources`: Active recipe website configurations
  - `user_settings`: Diet preferences and allergies
  - `hated_recipes` & `saved_recipes`: User personalization data
  - `agent_logs`: Activity logging for debugging

### Web Scraping and Crawling
- **httpx**: Async HTTP client for web requests
- **BeautifulSoup4**: HTML parsing and content extraction
- **Schema.org Support**: JSON-LD structured data parsing
- **Multiple Source Integration**: Dynamic recipe source management

## Key Components

### 1. Agent API (`agent_api.py`)
- Main FastAPI application with CORS support
- Single POST `/agent` endpoint for recipe discovery
- Health check endpoint for monitoring
- Error handling and logging

### 2. Recipe Processing Pipeline
- **Intent Extraction**: Analyzes user prompts for meal type, diet, and preferences
- **Prompt Enrichment**: Enhances prompts with user context and dietary restrictions
- **Keyword Optimization**: Generates targeted search terms for better results
- **Web Crawling**: Fetches and parses recipe content from multiple sources
- **Bulk Storage**: Efficient database insertion with user cleanup

### 3. User Context System
- **Preference Loading**: Retrieves user dietary restrictions and preferences
- **Content Filtering**: Excludes hated recipes and accommodates allergies
- **Personalization**: Tailors results based on user history and settings

### 4. Logging and Monitoring
- **Activity Logging**: Tracks agent runs for debugging and analytics
- **Error Handling**: Comprehensive exception management
- **Performance Monitoring**: Request/response tracking

## Data Flow

1. **Request Reception**: Frontend sends POST request to `/agent` with prompt and user_id
2. **User Context Loading**: System retrieves user preferences, dietary restrictions, and exclusions
3. **Prompt Processing**: OpenAI extracts intent and generates optimized search keywords
4. **Source Discovery**: Active recipe sources are fetched from database
5. **Web Crawling**: Multiple recipe websites are searched and scraped asynchronously
6. **Content Processing**: Raw HTML is parsed into structured recipe data
7. **User Filtering**: Results are filtered against user's hated recipes and dietary restrictions
8. **Bulk Storage**: Full recipe data is stored in database with user association
9. **Response Generation**: Limited recipe data (title, image, description) is returned to frontend
10. **Activity Logging**: Request details are logged for monitoring and debugging

## External Dependencies

### AI Services
- **OpenAI API**: GPT-4 model for natural language processing
- **API Key Required**: OPENAI_API_KEY environment variable

### Database
- **Supabase**: Managed PostgreSQL with real-time capabilities
- **Dual Access**: Standard client for queries, service role for system operations
- **Environment Variables**: SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY

### Web Scraping
- **Public Recipe Websites**: Configurable through recipe_sources table
- **User-Agent Rotation**: Professional browser identification
- **Rate Limiting**: Respectful crawling practices

## Deployment Strategy

### Production Environment
- **Replit Autoscale**: Automatic scaling based on demand
- **Gunicorn Server**: Multi-worker WSGI deployment
- **Port Configuration**: Internal 5000, external 80
- **Health Monitoring**: Built-in health check endpoint

### Development Environment
- **Local Testing**: Uvicorn development server with hot reload
- **CORS Configuration**: Localhost:5173 for Vite frontend development
- **Environment Management**: python-dotenv for local secrets

### Dependencies Management
- **pyproject.toml**: Modern Python project configuration
- **Key Packages**: FastAPI, OpenAI, Supabase, BeautifulSoup4, httpx
- **Version Pinning**: Specific versions for stability

## Changelog
- June 13, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.