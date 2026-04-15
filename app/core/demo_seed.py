from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.repositories.user_repo import UserRepository
from app.repositories.message_repo import ConversationRepository, MessageRepository
from app.models.message import Message


DEMO_USERS = [
    {
        "username": "demo_user_1",
        "email": "demo1@chatter.dev",
        "password": "demo12345",
        "display_name": "Alex (Demo 1)",
    },
    {
        "username": "demo_user_2",
        "email": "demo2@chatter.dev",
        "password": "demo12345",
        "display_name": "Sam (Demo 2)",
    },
]


async def ensure_demo_data() -> None:
    """Create two demo users and a direct conversation if missing."""
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        conv_repo = ConversationRepository(db)
        msg_repo = MessageRepository(db)

        users = []
        for demo in DEMO_USERS:
            user = await user_repo.get_by_email(demo["email"])
            if not user:
                user = await user_repo.create(
                    username=demo["username"],
                    email=demo["email"],
                    password=demo["password"],
                    display_name=demo["display_name"],
                )
            users.append(user)

        await db.flush()

        conv = await conv_repo.find_direct(users[0].id, users[1].id)
        if not conv:
            conv = await conv_repo.create(
                type="direct",
                created_by=users[0].id,
                participant_ids=[users[0].id, users[1].id],
            )

        existing_message = await db.execute(
            select(Message.id).where(Message.conversation_id == conv.id).limit(1)
        )
        if not existing_message.scalar_one_or_none():
            await msg_repo.create(
                conversation_id=conv.id,
                sender_id=users[0].id,
                content="Demo chat is ready. Start messaging and place a call.",
            )

        await db.commit()
