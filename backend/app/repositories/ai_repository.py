"""Database operations and LLM services for AI conversations"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import ASSISTANT
from app.core.exceptions import ConversationNotFoundError
from app.models.ai_model import Conversation, Message, Trip
from app.services.ai.providers.gemini import GeminiProvider

provider = GeminiProvider()

def start_conversation(db: Session, user):
    """Create a new conversation and associated trip for a user."""

    new_conversation = Conversation(
        user_id=user
    )

    new_trip = Trip()

    new_conversation.trip = new_trip

    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    return new_conversation.id

def get_conversation_by_id(conv_id, db: Session, user):
    """Retrieve a conversation belonging to the specified user."""

    statement = select(Conversation).where(
        Conversation.user_id == user,
        Conversation.id == conv_id
    )
    conversation = db.execute(statement).scalar_one_or_none()

    if not conversation:
        raise ConversationNotFoundError
    
    return conversation

def save_message(message: str, role: str, conv_id, db: Session):
    """Save a message to an existing conversation."""

    save_message = Message(
        conversation_id=conv_id,
        role=role,
        content=message
    )
    db.add(save_message)
    db.commit()

def load_chat_history(conv_id, db: Session, user):
    """Retrieve the most recent ten messages in chronological order."""

    statement = select(Message).join(Conversation).where(
        Message.conversation_id == conv_id,
        Conversation.user_id == user
    ).order_by(Message.created_at.desc()).limit(10)

    history = db.execute(statement).scalars().all()

    if not history:
        raise ValueError("Messages could not be retrieved.")

    in_order = []
    count = 0
    index = -1
    while count < len(history):
        in_order.append(history[index])
        index -= 1
        count += 1
        
    return in_order

def update_summary(conv_id, history: list[dict], db: Session, user):
    """Generate and save a conversation summary, removing older messages."""

    new_summary = provider.create_summary(history)

    update_statement = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == user
    )
    conversation = db.execute(update_statement).scalar_one_or_none()

    if not conversation:
        raise ValueError("Conversation not found.")
    
    conversation.summary = new_summary

    delete_statement = select(Message).where(
        Message.conversation_id == conv_id,
    ).order_by(
        Message.created_at
    )
    messages = db.execute(delete_statement).scalars().all()
    
    for message in messages[:-2]:
        db.delete(message)

    db.commit()

def load_chat_summary(conv_id, db: Session, user):
    """Retrieve the stored summary for a user's conversation."""

    conversation = get_conversation_by_id(conv_id, db, user)
    return conversation.summary

def get_last_message(conv_id, db: Session, user):
    """Retrieve the most recent assistant message from a user's conversation."""
    
    statement = select(Message.content).join(Conversation).where(
        Message.conversation_id == conv_id,
        Conversation.user_id == user,
        Message.role == ASSISTANT
    ).order_by(Message.created_at.desc()).limit(1)

    return db.execute(statement).scalar_one_or_none()


        



    


    











