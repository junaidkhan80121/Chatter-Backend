from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models as _models
from ..database import SessionLocal
from ..schemas import MessageCreate
from typing import List

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/send")
def send_message(payload: MessageCreate, db: Session = Depends(get_db)):
    # Minimal persistence of a message and placeholder for push via Redis pubsub
    # In real setup, validate conversation exists, user permissions, etc.
    msg = _models.Message(
        conversation_id=payload.conversation_id,
        sender_id=1,  # placeholder for authenticated user
        content=payload.content,
        status="sent",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "timestamp": str(msg.timestamp), "status": msg.status}
