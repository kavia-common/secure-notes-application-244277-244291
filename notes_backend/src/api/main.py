from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import get_db, Base, engine
from .models import User, UserCreate, UserResponse, Token, Tag, TagCreate, TagResponse, Note, NoteCreate, NoteUpdate, NoteResponse, SearchQuery
from .security import verify_password, get_password_hash, create_access_token, get_current_user

from pydantic import ValidationError

from starlette.responses import JSONResponse

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Secure Notes API",
    description="FastAPI backend for private, user-authenticated notes with tagging, favorite/pin, autosave, and search.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Users", "description": "User authentication and personal information"},
        {"name": "Notes", "description": "CRUD operations for notes"},
        {"name": "Tags", "description": "CRUD operations for tags"},
        {"name": "Search", "description": "Notes search operations"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- User/Auth Routes --------------------

@app.post("/auth/register", response_model=UserResponse, tags=['Users'])
# PUBLIC_INTERFACE
def register_user(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    """
    if db.query(User).filter(User.email == user_create.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user_create.password)
    user = User(email=user_create.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, email=user.email)

@app.post("/auth/login", response_model=Token, tags=['Users'])
# PUBLIC_INTERFACE
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate a user and return JWT access token.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse, tags=['Users'])
# PUBLIC_INTERFACE
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get info for the currently authenticated user.
    """
    return UserResponse(id=current_user.id, email=current_user.email)


# -------------------- Notes CRUD --------------------

@app.post("/notes/", response_model=NoteResponse, tags=["Notes"])
# PUBLIC_INTERFACE
def create_note(note: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new note for the authenticated user.
    """
    tag_objs = []
    if note.tag_ids:
        tag_objs = db.query(Tag).filter(Tag.id.in_(note.tag_ids), Tag.owner_id == current_user.id).all()
    db_note = Note(
        title=note.title,
        content=note.content,
        is_pinned=note.is_pinned,
        is_favorite=note.is_favorite,
        owner_id=current_user.id,
        tags=tag_objs,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


@app.get("/notes/", response_model=List[NoteResponse], tags=["Notes"])
# PUBLIC_INTERFACE
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    pinned: Optional[bool] = None,
    favorite: Optional[bool] = None,
    tag_ids: Optional[List[int]] = Query(None)
):
    """
    List notes for the authenticated user, with optional filters.
    """
    query = db.query(Note).filter(Note.owner_id == current_user.id)
    if pinned is not None:
        query = query.filter(Note.is_pinned == pinned)
    if favorite is not None:
        query = query.filter(Note.is_favorite == favorite)
    if tag_ids:
        query = query.filter(Note.tags.any(Tag.id.in_(tag_ids)))
    notes = query.order_by(Note.updated_at.desc()).offset(skip).limit(limit).all()
    return notes

@app.get("/notes/{note_id}", response_model=NoteResponse, tags=["Notes"])
# PUBLIC_INTERFACE
def get_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get a note by ID (must be owned by authenticated user).
    """
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.put("/notes/{note_id}", response_model=NoteResponse, tags=["Notes"])
# PUBLIC_INTERFACE
def update_note(note_id: int, note_update: NoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a note's title, content, pinned/favorite, or tags. Supports autosave via autosaved_content.
    """
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    # Autosave support (patch only autosaved_content if present)
    if note_update.autosaved_content is not None:
        note.autosaved_content = note_update.autosaved_content
        db.commit()
        db.refresh(note)
        return note
    # Standard updates
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    if note_update.is_pinned is not None:
        note.is_pinned = note_update.is_pinned
    if note_update.is_favorite is not None:
        note.is_favorite = note_update.is_favorite
    if note_update.tag_ids is not None:
        note.tags = db.query(Tag).filter(Tag.id.in_(note_update.tag_ids), Tag.owner_id == current_user.id).all()
    db.commit()
    db.refresh(note)
    return note

@app.delete("/notes/{note_id}", status_code=204, tags=["Notes"])
# PUBLIC_INTERFACE
def delete_note(note_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a note. Only the owner can delete.
    """
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return JSONResponse(status_code=204, content={})

# ----------- Tag APIs ------------

@app.post("/tags/", response_model=TagResponse, tags=["Tags"])
# PUBLIC_INTERFACE
def create_tag(tag: TagCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new tag for the authenticated user.
    """
    tag_obj = Tag(name=tag.name, owner_id=current_user.id)
    db.add(tag_obj)
    db.commit()
    db.refresh(tag_obj)
    return tag_obj

@app.get("/tags/", response_model=List[TagResponse], tags=["Tags"])
# PUBLIC_INTERFACE
def list_tags(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    List tags belonging to the authenticated user.
    """
    tags = db.query(Tag).filter(Tag.owner_id == current_user.id).all()
    return tags

@app.delete("/tags/{tag_id}", status_code=204, tags=["Tags"])
# PUBLIC_INTERFACE
def delete_tag(tag_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a tag owned by the user. Also removes it from notes.
    """
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.owner_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    for note in tag.notes:
        if tag in note.tags:
            note.tags.remove(tag)
    db.delete(tag)
    db.commit()
    return JSONResponse(status_code=204, content={})

# ----------- Notes Search ----------

@app.post("/notes/search", response_model=List[NoteResponse], tags=["Search"])
# PUBLIC_INTERFACE
def search_notes(
    search: SearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
):
    """
    Search notes by text and (optionally) by tags, pin/favorite status.
    """
    query = db.query(Note).filter(Note.owner_id == current_user.id)
    if search.query:
        filter_text = f"%{search.query.strip()}%"
        query = query.filter((Note.title.ilike(filter_text)) | (Note.content.ilike(filter_text)))
    if search.tag_ids:
        query = query.filter(Note.tags.any(Tag.id.in_(search.tag_ids)))
    if search.is_pinned is not None:
        query = query.filter(Note.is_pinned == search.is_pinned)
    if search.is_favorite is not None:
        query = query.filter(Note.is_favorite == search.is_favorite)
    results = query.order_by(Note.updated_at.desc()).offset(skip).limit(limit).all()
    return results


# ----------- Root & Health ----------

@app.get("/", tags=["Health"])
# PUBLIC_INTERFACE
def health_check():
    """Health check for API."""
    return {"message": "Healthy"}

# Error handler for validation
@app.exception_handler(ValidationError)
def pydantic_validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
