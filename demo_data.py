#!/usr/bin/env python3
"""
Demo data population script for Hackathon API
Creates users and posts for demonstration purposes
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust this to match your API URL

# Demo users data
DEMO_USERS = [
    {
        "username": "alice_smith",
        "password": "demo123",
        "display_name": "Alice Smith",
        "avatar": "https://i.pravatar.cc/150?img=1",
    },
    {
        "username": "bob_johnson",
        "password": "demo123",
        "display_name": "Bob Johnson",
        "avatar": "https://i.pravatar.cc/150?img=3",
    },
    {
        "username": "carol_davis",
        "password": "demo123",
        "display_name": "Carol Davis",
        "avatar": "https://i.pravatar.cc/150?img=5",
    },
    {
        "username": "david_wilson",
        "password": "demo123",
        "display_name": "David Wilson",
        "avatar": "https://i.pravatar.cc/150?img=7",
    },
    {
        "username": "emma_brown",
        "password": "demo123",
        "display_name": "Emma Brown",
        "avatar": "https://i.pravatar.cc/150?img=9",
    },
]

# Demo posts content
DEMO_POSTS = [
    {
        "content": "Just launched my new project! Excited to share it with everyone. It's been months of hard work but totally worth it.",
        "voice_style": "enthusiastic",
    },
    {
        "content": "Beautiful sunset today. Sometimes you need to stop and appreciate the simple things in life.",
        "voice_style": "calm",
    },
    {
        "content": "Working on some machine learning algorithms. The latest model is showing promising results with 94% accuracy!",
        "voice_style": "professional",
    },
    {
        "content": "Coffee break thoughts: Why do we call it 'rush hour' when nobody's moving? 🤔",
        "voice_style": "casual",
    },
    {
        "content": "Finished reading 'The Pragmatic Programmer' - highly recommend it to anyone in tech. So many valuable insights!",
        "voice_style": "thoughtful",
    },
    {
        "content": "Team meeting went great today. Love working with passionate people who share the same vision.",
        "voice_style": "positive",
    },
    {
        "content": "Debugging is like being a detective in a crime movie where you are also the murderer. Anyone else relate?",
        "voice_style": "humorous",
    },
    {
        "content": "Nature walk this morning really helped clear my mind. Fresh air and exercise are the best productivity boosters.",
        "voice_style": "reflective",
    },
    {
        "content": "Just discovered this amazing new restaurant downtown. The pasta was incredible - definitely going back!",
        "voice_style": "excited",
    },
    {
        "content": "Learning new programming languages is like collecting tools for your toolbox. Each one has its perfect use case.",
        "voice_style": "educational",
    },
]


class HackathonAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.users_tokens = {}  # Store user tokens

    def register_user(self, user_data: Dict) -> Dict:
        """Register a new user"""
        url = f"{self.base_url}/api/auth/register"
        response = self.session.post(url, json=user_data)
        response.raise_for_status()
        return response.json()

    def login_user(self, username: str, password: str) -> str:
        """Login user and return token"""
        url = f"{self.base_url}/api/auth/login"
        data = {"username": username, "password": password}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]

    def create_post(self, token: str, content: str, voice_style: str = "natural") -> Dict:
        """Create a text post"""
        url = f"{self.base_url}/api/posts/"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"content": content, "voice_style": voice_style}
        response = self.session.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    def get_posts(self, token: str, skip: int = 0, limit: int = 10) -> Dict:
        """Get posts"""
        url = f"{self.base_url}/api/posts/"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"skip": skip, "limit": limit}
        response = self.session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def main():
    print("🚀 Starting demo data population for Hackathon API")
    print(f"API Base URL: {API_BASE_URL}")
    print("-" * 50)

    client = HackathonAPIClient(API_BASE_URL)

    # Step 1: Register users
    print("👥 Registering demo users...")
    registered_users = []

    for i, user_data in enumerate(DEMO_USERS, 1):
        try:
            print(f"  {i}. Registering {user_data['username']}...", end=" ")
            user_response = client.register_user(user_data)

            # Login to get token
            token = client.login_user(user_data["username"], user_data["password"])
            client.users_tokens[user_data["username"]] = token

            registered_users.append({"user_data": user_response, "username": user_data["username"], "token": token})
            print("✅ Success")

        except requests.exceptions.HTTPError as e:
            print(f"❌ Failed: {e}")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    print(f"\n✅ Successfully registered {len(registered_users)} users")

    # Step 2: Create posts
    print("\n📝 Creating demo posts...")
    created_posts = []

    for i, post_data in enumerate(DEMO_POSTS, 1):
        try:
            # Randomly assign posts to users
            user = registered_users[i % len(registered_users)]
            username = user["username"]
            token = user["token"]

            print(f"  {i}. Creating post by {username}...", end=" ")
            post_response = client.create_post(
                token=token, content=post_data["content"], voice_style=post_data["voice_style"]
            )
            created_posts.append(post_response)
            print("✅ Success")

            # Small delay to avoid overwhelming the API
            time.sleep(0.5)

        except requests.exceptions.HTTPError as e:
            print(f"❌ Failed: {e}")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    print(f"\n✅ Successfully created {len(created_posts)} posts")

    # Step 3: Display summary
    print("\n" + "=" * 50)
    print("📊 DEMO DATA SUMMARY")
    print("=" * 50)
    print(f"👥 Users created: {len(registered_users)}")
    print(f"📝 Posts created: {len(created_posts)}")

    if registered_users:
        print("\n👥 Demo Users:")
        for user in registered_users:
            user_data = user["user_data"]
            print(f"  • {user_data.get('display_name', 'N/A')} (@{user_data['username']}) - ID: {user_data['id']}")

    if created_posts:
        print(f"\n📝 Sample Posts:")
        for i, post in enumerate(created_posts[:3], 1):
            content_preview = post["content"][:60] + "..." if len(post["content"]) > 60 else post["content"]
            print(f"  {i}. {post['username']}: \"{content_preview}\"")

        if len(created_posts) > 3:
            print(f"  ... and {len(created_posts) - 3} more posts")

    # Step 4: Verify by fetching posts
    if registered_users:
        print("\n🔍 Verifying data by fetching posts...")
        try:
            # Use first user's token to fetch posts
            token = registered_users[0]["token"]
            posts_response = client.get_posts(token, limit=20)
            total_posts = posts_response.get("total", 0)
            print(f"✅ API reports {total_posts} total posts in the system")

        except Exception as e:
            print(f"❌ Error verifying data: {e}")

    print("\n🎉 Demo data population completed!")
    print("\nLogin credentials for testing:")
    print("Username: alice_smith | Password: demo123")
    print("Username: bob_johnson | Password: demo123")
    print("(All demo users use password: demo123)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        import traceback

        traceback.print_exc()
