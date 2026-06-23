#!/usr/bin/env python3
"""
Jira Configuration Test Script
Run this to verify your Jira credentials are working.
"""

import sys
import os
sys.path.append('.')

from app.core.config import settings
from app.services.jira_client import JiraClient

def test_jira_config():
    print("🔍 Testing Jira Configuration...")
    print()

    # Check configuration
    print("📋 Current Configuration:")
    print(f"   Base URL: {settings.jira_base_url}")
    print(f"   Email: {settings.jira_email}")
    print(f"   Token: {'***' + settings.jira_api_token[-4:] if settings.jira_api_token and len(settings.jira_api_token) > 4 else 'Not set'}")
    print()

    # Test client initialization
    try:
        client = JiraClient()
        print("✅ JiraClient initialized successfully")
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

    # Test API connection (optional - requires valid credentials)
    try:
        print("🔗 Testing API connection...")
        # This will fail with placeholder credentials, but shows the connection attempt
        projects = client.get_projects()
        print(f"✅ Connected! Found {len(projects)} projects")
        return True
    except Exception as e:
        if "placeholder" in str(e).lower() or "your-domain" in str(e).lower():
            print("⚠️  Using placeholder credentials - update .env file")
            return False
        else:
            print(f"❌ API Error: {e}")
            return False

if __name__ == "__main__":
    success = test_jira_config()
    if success:
        print("\n🎉 Jira configuration is working!")
    else:
        print("\n📝 Please update your .env file with real Jira credentials")
        print("   Then run: python test_jira.py")
    sys.exit(0 if success else 1)