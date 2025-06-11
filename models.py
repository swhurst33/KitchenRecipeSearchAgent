"""
Pydantic models for Kitchnsync Recipe Discovery Agent
"""

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from uuid import UUID


class AgentRequest(BaseModel):
    """Request model for the recipe discovery agent"""

    prompt: str
    user_id: str


class RecipeIntent(BaseModel):
    """Intent extracted from user prompt"""

    meal_type: Optional[str] = None
    diet_type: Optional[str] = None
    keywords: List[str] = []
    time_constraint: Optional[str] = None
    cuisine_type: Optional[str] = None


class RecipeResponse(BaseModel):
    """Recipe response model for frontend (limited fields)"""

    title: str
    image_url: Optional[HttpUrl] = None
    description: Optional[str] = None
    recipe_id: str


class AgentResponse(BaseModel):
    """Response model for the agent endpoint"""

    recipes: List[RecipeResponse]
    message: Optional[str] = None


class IngredientModel(BaseModel):
    """Full ingredient model for storage"""

    text: str
    quantity: Optional[float] = None
    unit: Optional[str] = None


class NutritionModel(BaseModel):
    """Nutrition information model"""

    calories: Optional[int] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None


class FullRecipeModel(BaseModel):
    """Complete recipe model for storage in Supabase"""

    recipe_id: str
    title: str
    description: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    source_url: HttpUrl
    ingredients: List[IngredientModel]
    instructions: List[str]
    nutrition: Optional[NutritionModel] = None
    prep_time: Optional[int] = None  # minutes
    cook_time: Optional[int] = None  # minutes
    servings: Optional[int] = None
    difficulty: Optional[str] = None
    cuisine_type: Optional[str] = None
    meal_type: Optional[str] = None
    diet_tags: List[str] = []


class RecipeSource(BaseModel):
    """Recipe source from Supabase"""

    id: int
    name: str
    base_url: str
    search_pattern: str
    is_active: bool = True


class HatedRecipe(BaseModel):
    """Hated recipe filter from Supabase"""

    user_id: str
    recipe_title: str
    recipe_url: Optional[str] = None
