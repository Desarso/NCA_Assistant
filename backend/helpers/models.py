from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine
from sqlalchemy import String, Column

# Define the database URL
DATABASE_URL = "sqlite:///./chat_history.sqlite"

# Create models matching your frontend Prisma schema
class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    email: str = Field(unique=True)
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now, sa_column=Column(String))
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(String))
    
    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Foreign keys
    user_id: str = Field(foreign_key="user.id")
    
    # Relationships
    user: User = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    is_user_message: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Foreign keys
    conversation_id: str = Field(foreign_key="conversation.id")
    
    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")


# Setup database connection
engine = create_engine(DATABASE_URL, echo=False)


# Function to create all tables in the database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Database session management
def get_session():
    with Session(engine) as session:
        yield session