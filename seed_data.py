# seed_data.py
# Optional: Create some sample users and posts for testing

import asyncio
from app.tables import User, Post, PostLike
from app.auth import get_password_hash


async def create_seed_data():
    try:
        print("🌱 Creating seed data...")

        # Create sample users
        user1 = User(
            username="demo_user",
            hashed_password=get_password_hash("password123"),
            display_name="Demo User",
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=demo_user",
        )
        await user1.save()

        user2 = User(
            username="jane_doe",
            hashed_password=get_password_hash("password123"),
            display_name="Jane Doe",
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=jane_doe",
        )
        await user2.save()

        user3 = User(
            username="voice_master",
            hashed_password=get_password_hash("password123"),
            display_name="Voice Master",
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=voice_master",
        )
        await user3.save()

        print(f"✅ Created users: {user1.id}, {user2.id}, {user3.id}")

        # Create sample posts
        post1 = Post(
            text_content="Welcome to Echo! This is my first voice note.",
            voice_file_path="https://example.com/audio1.mp3",
            duration=15.5,
            voice_style="natural",
            likes=5,
            replies_count=2,
            listen_count=25,
            tags=["welcome", "first-post"],
            author=user1.id,
        )
        await post1.save()

        post2 = Post(
            text_content="Just had an amazing coffee! The weather is perfect today.",
            voice_file_path="https://example.com/audio2.mp3",
            duration=8.2,
            voice_style="energetic",
            likes=12,
            replies_count=0,
            listen_count=45,
            tags=["coffee", "weather"],
            author=user2.id,
        )
        await post2.save()

        post3 = Post(
            text_content="Some thoughts on productivity and time management...",
            voice_file_path="https://example.com/audio3.mp3",
            duration=32.1,
            voice_style="calm",
            likes=8,
            replies_count=1,
            listen_count=67,
            tags=["productivity", "tips"],
            author=user3.id,
        )
        await post3.save()

        # Create a reply to post1
        reply1 = Post(
            text_content="Great to have you here! Welcome aboard!",
            voice_file_path="https://example.com/reply1.mp3",
            duration=6.8,
            voice_style="natural",
            likes=3,
            replies_count=0,
            listen_count=12,
            tags=["welcome"],
            author=user2.id,
            parent_post=post1.id,
        )
        await reply1.save()

        print(f"✅ Created posts: {post1.id}, {post2.id}, {post3.id}, {reply1.id}")

        # Create some likes
        like1 = PostLike(user=user2.id, post=post1.id)
        await like1.save()

        like2 = PostLike(user=user3.id, post=post1.id)
        await like2.save()

        like3 = PostLike(user=user1.id, post=post2.id)
        await like3.save()

        print("✅ Created sample likes")

        print("🎉 Seed data created successfully!")
        print("\nSample login credentials:")
        print("Username: demo_user, Password: password123")
        print("Username: jane_doe, Password: password123")
        print("Username: voice_master, Password: password123")

    except Exception as e:
        print(f"❌ Error creating seed data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_seed_data())
