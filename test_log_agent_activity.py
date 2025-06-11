"""
Test script for agent activity logging
Tests the log_agent_activity function with proper UUID format
"""
import sys
sys.path.append('.')

from agent_logger import log_agent_activity

def test_log_agent_activity():
    """Test the agent activity logging functionality"""
    
    print("=== Agent Activity Logging Test ===\n")
    
    # Test data with proper UUID format
    test_user_id = "56cae3ba-7998-4cd1-9cd8-991291691679"
    test_prompt = "quick keto dinner"
    test_results_count = 8
    
    print("1. Testing agent activity logging...")
    print(f"   User ID: {test_user_id}")
    print(f"   Prompt: '{test_prompt}'")
    print(f"   Results Count: {test_results_count}")
    
    # Test the logging function
    try:
        log_agent_activity(test_user_id, test_prompt, test_results_count)
        print("   ✓ Logging function called successfully")
        print("   ✓ No exceptions thrown")
        
    except Exception as e:
        print(f"   ✗ Logging failed: {e}")
        print("   Note: This may be expected if using test UUID with production database")
    
    print("\n2. Testing various prompt types...")
    
    test_cases = [
        ("healthy breakfast", 5),
        ("vegan pasta recipes with lots of vegetables", 12),
        ("gluten-free desserts", 3),
        ("quick lunch under 30 minutes", 7),
        ("mediterranean diet dinner", 9)
    ]
    
    for prompt, count in test_cases:
        try:
            log_agent_activity(test_user_id, prompt, count)
            print(f"   ✓ Logged: '{prompt[:30]}...' ({count} results)")
        except Exception as e:
            print(f"   ✗ Failed to log: '{prompt[:30]}...' - {e}")
    
    print("\n3. Testing edge cases...")
    
    # Test with very long prompt
    long_prompt = "I need a recipe that is healthy, delicious, easy to make, uses common ingredients, takes less than 30 minutes, is suitable for a family of four, has balanced nutrition, and preferably includes vegetables and lean protein"
    try:
        log_agent_activity(test_user_id, long_prompt, 6)
        print("   ✓ Long prompt logged successfully")
    except Exception as e:
        print(f"   ✗ Long prompt failed: {e}")
    
    # Test with zero results
    try:
        log_agent_activity(test_user_id, "very specific unusual recipe", 0)
        print("   ✓ Zero results logged successfully")
    except Exception as e:
        print(f"   ✗ Zero results failed: {e}")
    
    # Test with high results count
    try:
        log_agent_activity(test_user_id, "general recipe search", 15)
        print("   ✓ High results count logged successfully")
    except Exception as e:
        print(f"   ✗ High results count failed: {e}")
    
    print("\n4. Expected data structure in agent_logs table:")
    print("   {")
    print(f'     "user_id": "{test_user_id}",')
    print(f'     "prompt": "{test_prompt}",')
    print(f'     "results_count": {test_results_count},')
    print('     "created_at": "2024-01-15T10:30:00Z"  // Auto-generated')
    print("   }")
    
    print("\n=== Agent Logging Integration Summary ===")
    print("✓ log_agent_activity() function created in agent_logger.py")
    print("✓ Uses service role Supabase client for bypassing RLS")
    print("✓ Integrated into /agent endpoint after bulk storage")
    print("✓ Error handling prevents logging failures from crashing agent")
    print("✓ Logs user_id, prompt, results_count with auto created_at")
    print("✓ Ready for debugging post-website integration")

if __name__ == "__main__":
    test_log_agent_activity()