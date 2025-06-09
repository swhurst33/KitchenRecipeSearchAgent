#!/usr/bin/env python3
import subprocess
import json

def test_curl_command():
    """Execute the exact curl command and show results"""
    
    curl_command = [
        'curl', '-X', 'POST', 
        'https://kitchen-recipe-agent-swhurst33.replit.app/agent',
        '-H', 'Content-Type: application/json',
        '-d', '{"prompt": "quick keto dinner", "user_id": "test-123"}',
        '--silent', '--show-error'
    ]
    
    print("Executing curl command:")
    print("curl -X POST https://kitchen-recipe-agent-swhurst33.replit.app/agent \\")
    print("-H \"Content-Type: application/json\" \\")
    print("-d '{\"prompt\": \"quick keto dinner\", \"user_id\": \"test-123\"}'")
    print()
    print("Response from API:")
    print("-" * 50)
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=45)
        
        if result.returncode == 0:
            try:
                # Try to parse as JSON and format nicely
                response_data = json.loads(result.stdout)
                print(json.dumps(response_data, indent=2))
            except json.JSONDecodeError:
                # If not valid JSON, print raw response
                print(result.stdout)
        else:
            print(f"Error (exit code {result.returncode}):")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("Request timed out after 45 seconds")
    except Exception as e:
        print(f"Command failed: {e}")

if __name__ == "__main__":
    test_curl_command()