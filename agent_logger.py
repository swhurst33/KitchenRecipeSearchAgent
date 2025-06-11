"""
Agent Activity Logger for KitchenSync Recipe Discovery Agent
Logs agent runs to agent_logs table for debugging post-website integration
"""

import logging
import os
from supabase import create_client, Client

logger = logging.getLogger(__name__)


def get_supabase_service_client() -> Client:
    """Initialize Supabase client with service role key for bypassing RLS"""
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set"
        )

    return create_client(url, service_key)


def log_agent_activity(user_id: str, prompt: str, results_count: int) -> None:
    """
    Log agent activity to agent_logs table for debugging

    Args:
        user_id: User ID who made the request
        prompt: The original prompt from the user
        results_count: Number of recipes successfully stored

    Note: created_at is set automatically by the database
    """
    try:
        supabase = get_supabase_service_client()

        # Prepare log data
        log_data = {
            "user_id": user_id,
            "prompt": prompt,
            "results_count": results_count,
            # created_at is handled by database default
        }

        # Insert into agent_logs table
        response = supabase.table("agent_logs").insert(log_data).execute()

        if response.data:
            logger.info(
                f"✓ Logged agent activity for user {user_id}: {results_count} results for prompt '{prompt[:50]}...'"
            )
        else:
            logger.warning(f"No data returned when logging activity for user {user_id}")

    except Exception as e:
        # Don't crash the agent if logging fails - just log the error
        logger.error(f"Failed to log agent activity for user {user_id}: {e}")
        print(f"Agent logging error: {e}")  # Also print to console for debugging
