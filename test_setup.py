#!/usr/bin/env python3
"""
Test script to validate Spotted Leaderboard setup before deployment.
Run this to ensure all configurations are correct.
"""

import os
import sys
from dotenv import load_dotenv

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(status, message):
    """Print colored status message"""
    if status == "success":
        print(f"{GREEN}✅ {message}{RESET}")
    elif status == "error":
        print(f"{RED}❌ {message}{RESET}")
    elif status == "warning":
        print(f"{YELLOW}⚠️  {message}{RESET}")
    elif status == "info":
        print(f"{BLUE}ℹ️  {message}{RESET}")

def test_environment_variables():
    """Test that all required environment variables are set"""
    print("\n" + "="*50)
    print("Testing Environment Variables")
    print("="*50)
    
    load_dotenv()
    
    required_vars = {
        "SLACK_BOT_TOKEN": "xoxb-",
        "SLACK_APP_TOKEN": "xapp-",
        "SPOTTED_CHANNEL_ID": "C",
        "SUPABASE_URL": "https://",
        "SUPABASE_KEY": None  # No prefix check
    }
    
    all_good = True
    for var, prefix in required_vars.items():
        value = os.environ.get(var)
        if not value:
            print_status("error", f"{var} is not set")
            all_good = False
        elif prefix and not value.startswith(prefix):
            print_status("error", f"{var} has invalid format (should start with '{prefix}')")
            all_good = False
        else:
            # Mask sensitive values
            masked_value = value[:10] + "..." if len(value) > 10 else "***"
            print_status("success", f"{var} = {masked_value}")
    
    # Optional variables
    port = os.environ.get("PORT", "5000 (default)")
    print_status("info", f"PORT = {port}")
    
    ssl_verify = os.environ.get("DISABLE_SSL_VERIFY", "false (default)")
    if ssl_verify.lower() == "true":
        print_status("warning", "SSL verification is DISABLED (only use for development)")
    else:
        print_status("success", "SSL verification is ENABLED")
    
    return all_good

def test_database_connection():
    """Test connection to Supabase"""
    print("\n" + "="*50)
    print("Testing Database Connection")
    print("="*50)
    
    try:
        from database import Database
        db = Database()
        print_status("success", "Connected to Supabase")
        
        # Try to fetch leaderboard
        scores = db.get_leaderboard(limit=5)
        print_status("success", f"Fetched leaderboard ({len(scores)} entries)")
        
        if scores:
            print_status("info", "Top score:")
            for user_id, user_name, score in scores[:1]:
                print(f"  {user_name or user_id}: {score}")
        else:
            print_status("info", "Leaderboard is empty (this is OK for new setup)")
        
        return True
    except ValueError as e:
        print_status("error", f"Database configuration error: {e}")
        return False
    except Exception as e:
        print_status("error", f"Failed to connect to database: {e}")
        print_status("info", "Check your SUPABASE_URL and SUPABASE_KEY")
        return False

def test_slack_connection():
    """Test connection to Slack"""
    print("\n" + "="*50)
    print("Testing Slack Connection")
    print("="*50)
    
    try:
        from slack_sdk import WebClient
        
        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        if not bot_token:
            print_status("error", "SLACK_BOT_TOKEN not set")
            return False
        
        client = WebClient(token=bot_token)
        
        # Test bot token
        auth = client.auth_test()
        print_status("success", f"Bot authenticated as: {auth['bot_id']}")
        print_status("info", f"Workspace: {auth['team']}")
        
        # Test channel access
        channel_id = os.environ.get("SPOTTED_CHANNEL_ID")
        try:
            channel_info = client.conversations_info(channel=channel_id)
            print_status("success", f"Channel accessible: #{channel_info['channel']['name']}")
        except Exception as e:
            print_status("error", f"Cannot access channel: {e}")
            print_status("info", "Make sure bot is invited to the channel")
            return False
        
        return True
    except Exception as e:
        print_status("error", f"Slack connection failed: {e}")
        print_status("info", "Check your SLACK_BOT_TOKEN")
        return False

def test_imports():
    """Test that all required packages are installed"""
    print("\n" + "="*50)
    print("Testing Python Packages")
    print("="*50)
    
    packages = [
        "slack_bolt",
        "slack_sdk",
        "flask",
        "flask_cors",
        "supabase",
        "dotenv",
    ]
    
    all_good = True
    for package in packages:
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package.replace("-", "_"))
            print_status("success", f"{package} is installed")
        except ImportError:
            print_status("error", f"{package} is not installed")
            all_good = False
    
    return all_good

def test_api():
    """Test that API can start"""
    print("\n" + "="*50)
    print("Testing API Configuration")
    print("="*50)
    
    try:
        from api import app
        print_status("success", "API app loaded successfully")
        
        # Test routes are registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/api/leaderboard', '/api/score/<user_id>', '/api/stats']
        
        for route in expected_routes:
            # Handle Flask's <> syntax
            route_pattern = route.replace('<', '').replace('>', '').split('user_id')[0] if '<' in route else route
            matching = [r for r in routes if route_pattern in r.replace('<', '').replace('>', '')]
            if matching:
                print_status("success", f"Route registered: {route}")
            else:
                print_status("error", f"Route missing: {route}")
        
        return True
    except Exception as e:
        print_status("error", f"API failed to load: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Spotted Leaderboard Setup Test")
    print("="*60)
    print("This script will validate your configuration before deployment.")
    print()
    
    results = {
        "Environment Variables": test_environment_variables(),
        "Python Packages": test_imports(),
        "Database Connection": test_database_connection(),
        "Slack Connection": test_slack_connection(),
        "API Configuration": test_api(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        if passed:
            print_status("success", f"{test_name}: PASSED")
        else:
            print_status("error", f"{test_name}: FAILED")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print_status("success", "All tests passed! ✨ You're ready to deploy!")
        print_status("info", "Run: python main.py")
        return 0
    else:
        print_status("error", "Some tests failed. Please fix the issues above.")
        print_status("info", "Check DEPLOYMENT_GUIDE.md for troubleshooting")
        return 1

if __name__ == "__main__":
    sys.exit(main())

