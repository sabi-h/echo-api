# fresh_db_setup.py
# This script will drop all tables and recreate them with the new schema

import asyncio
from app.tables import User, Post, PostLike


async def fresh_setup():
    try:
        print("🗑️  Dropping existing tables...")

        # Drop tables in reverse order to handle foreign key constraints
        await PostLike.alter().drop_table(if_exists=True)
        await Post.alter().drop_table(if_exists=True)
        await User.alter().drop_table(if_exists=True)

        print("✅ All tables dropped successfully!")

        print("🔨 Creating tables with new schema...")

        # Create tables in correct order
        await User.create_table(if_not_exists=True)
        await Post.create_table(if_not_exists=True)
        await PostLike.create_table(if_not_exists=True)

        print("✅ All tables created successfully!")

        print("🎉 Database setup complete! You can now start fresh.")

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(fresh_setup())
