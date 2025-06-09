from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from enum import Enum

class IngredientModel(BaseModel):
    text: str
    quantity: Optional[float] = None
    unit: Optional[str] = None

class MacrosModel(BaseModel):
    calories: Optional[int] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbs: Optional[float] = None

class RecipeModel(BaseModel):
    title: str
    image_url: Optional[HttpUrl] = None
    source_url: HttpUrl
    ingredients: List[IngredientModel]
    instructions: List[str]
    macros: Optional[MacrosModel] = None

class AgentRequest(BaseModel):
    prompt: str

class AgentResponse(BaseModel):
    recipes: List[RecipeModel]
    message: Optional[str] = None

class IntentExtraction(BaseModel):
    meal_type: Optional[str] = None
    diet_type: Optional[str] = None
    keywords: List[str] = []
    time_constraint: Optional[str] = None
    search_queries: List[str] = []
