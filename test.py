import asyncpg
import asyncio
import os


async def test_connection():
    try:
        conn = await asyncpg.connect(
            host="aws-0-eu-west-2.pooler.supabase.com",
            port=5432,
            user="postgres.xhvgljsruowihebavemy",
            password="LptYoVRuxDbaQzcS",
            database="postgres",
        )
        print("✅ Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")


asyncio.run(test_connection())
