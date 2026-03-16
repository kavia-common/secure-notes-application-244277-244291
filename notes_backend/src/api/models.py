"""
SQLAlchemy models and Pydantic schemas for FastAPI Notes App.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean, Text, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Many-to-Many association for Note <-> Tag
note_tag_association = Table(
    "note_tag_association",
    Base.metadata,
    Column("note_id", Integer, ForeignKey("notes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    notes = relationship("Note", back_populates="owner")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")
    notes = relationship("Note", secondary=note_tag_association, back_populates="tags")

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256))
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_pinned = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    autosaved_content = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary=note_tag_association, back_populates="notes")


# ---------- Pydantic Schemas ----------

# User schemas
class UserCreate(BaseModel):
    email: str = Field(..., description="User's unique email")
    password: str = Field(..., min_length=6, description="User's password")

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        orm_mode = True

# Auth/JWT schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None

# Tag schemas
class TagBase(BaseModel):
    name: str = Field(..., max_length=64)

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int
    class Config:
        orm_mode = True

# Note schemas
class NoteBase(BaseModel):
    title: str = Field(..., max_length=256)
    content: str = Field(..., description="Full note content")
    is_pinned: Optional[bool] = False
    is_favorite: Optional[bool] = False
    tag_ids: Optional[List[int]] = []

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_favorite: Optional[bool] = None
    tag_ids: Optional[List[int]] = None
    autosaved_content: Optional[str] = None  # for autosave

class NoteResponse(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse]

    class Config:
        orm_mode = True

class SearchQuery(BaseModel):
    query: Optional[str] = ""
    tag_ids: Optional[List[int]] = []
    is_pinned: Optional[bool] = None
    is_favorite: Optional[bool] = None
