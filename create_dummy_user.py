import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash

async def create_dummy_user():
    async with async_session_maker() as session:
        # Check if user already exists
        # In a generic way without querying
        
        dummy_user = User(
            username="dummy_user",
            email="dummy@example.com",
            hashed_password=get_password_hash("password123"),
            display_name="Dummy Tester",
            status="online"
        )
        
        session.add(dummy_user)
        try:
            await session.commit()
            print("Successfully created dummy user!")
            print("Email: dummy@example.com")
            print("Password: password123")
        except Exception as e:
            print(f"Failed to create user (might already exist): {e}")

if __name__ == "__main__":
    asyncio.run(create_dummy_user())
