"""Change admin dashboard password to a strong value."""
import asyncio
import bcrypt
import asyncpg
import os

NEW_PASSWORD = "Pr0vaani!Akruti#2026"

async def main():
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        db_url = "postgresql://postgres:764bb6070f6109033d7369b429ae6e6ac3aca26b84c1f84e@postgres:5432/postgres"
    
    hashed = bcrypt.hashpw(NEW_PASSWORD.encode(), bcrypt.gensalt()).decode()
    print(f"Generated bcrypt hash: {hashed[:20]}...")
    
    conn = await asyncpg.connect(db_url)
    
    result = await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE email IN ('admin@provaani.xyz', 'admin@sukanya.com')",
        hashed
    )
    print(f"DB result: {result}")
    
    rows = await conn.fetch("SELECT id, email FROM users")
    for row in rows:
        print(f"  User {row['id']}: {row['email']}")
    
    await conn.close()
    print(f"\n✅ Dashboard password changed to: {NEW_PASSWORD}")

if __name__ == "__main__":
    asyncio.run(main())
