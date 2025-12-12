import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# PUBLIC_INTERFACE
def get_database_url() -> str:
    """Get the database URL from environment variables.

    The function reads DATABASE_URL first. If not set, it tries to construct a URL
    from POSTGRES_URL or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_PORT.
    A final fallback uses a local preview-friendly URL.

    Env vars required (documented in .env.example):
    - DATABASE_URL (optional preferred)
    - POSTGRES_URL (optional)
    - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT (optional)
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Sometimes the database container provides a full URL
    pg_full = os.getenv("POSTGRES_URL")
    if pg_full:
        return pg_full

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5001")  # per preview instructions
    db = os.getenv("POSTGRES_DB", "postgres")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = get_database_url()

# SQLAlchemy setup
# Using psycopg (psycopg3) driver
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Note(Base):
    """SQLAlchemy model for notes table."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Pydantic Schemas
class NoteBase(BaseModel):
    title: str = Field(..., description="Title of the note", min_length=1, max_length=255)
    content: Optional[str] = Field(None, description="Content of the note")


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the note", min_length=1, max_length=255)
    content: Optional[str] = Field(None, description="Updated content of the note")


class NoteOut(NoteBase):
    id: int = Field(..., description="Primary key of the note")
    created_at: datetime = Field(..., description="Note creation timestamp")
    updated_at: datetime = Field(..., description="Note last update timestamp")

    class Config:
        from_attributes = True


# FastAPI app
app = FastAPI(
    title="Notes API",
    description="Simple Notes app backend with CRUD endpoints for notes (title, content).",
    version="1.0.0",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints."},
        {"name": "Notes", "description": "CRUD operations for notes."},
    ],
)

# CORS for frontend at 3000
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    """Dependency to get a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    """Create all tables on startup for simplicity."""
    Base.metadata.create_all(bind=engine)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check")
def health_check():
    """Health check endpoint.

    Returns:
        JSON object with message indicating health.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get("/notes", response_model=List[NoteOut], tags=["Notes"], summary="List notes")
def list_notes(db: Session = Depends(get_db)):
    """List all notes.

    Returns:
        List of NoteOut objects in ascending id order.
    """
    return db.query(Note).order_by(Note.id.asc()).all()


# PUBLIC_INTERFACE
@app.get("/notes/{note_id}", response_model=NoteOut, tags=["Notes"], summary="Get note by ID")
def get_note(note_id: int, db: Session = Depends(get_db)):
    """Fetch a note by its ID.

    Parameters:
        note_id: The ID of the note to fetch.

    Returns:
        The NoteOut object.

    Raises:
        HTTPException 404 if not found.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@app.post("/notes", response_model=NoteOut, status_code=201, tags=["Notes"], summary="Create a new note")
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    """Create a new note.

    Body:
        NoteCreate with required title and optional content.

    Returns:
        Newly created NoteOut.
    """
    note = Note(title=payload.title, content=payload.content or "")
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# PUBLIC_INTERFACE
@app.put("/notes/{note_id}", response_model=NoteOut, tags=["Notes"], summary="Update an existing note")
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    """Update an existing note by ID.

    Parameters:
        note_id: The ID of the note to update.

    Body:
        NoteUpdate with fields to modify.

    Returns:
        Updated NoteOut.

    Raises:
        HTTPException 404 if not found.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        if payload.title.strip() == "":
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content

    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# PUBLIC_INTERFACE
@app.delete("/notes/{note_id}", status_code=204, tags=["Notes"], summary="Delete a note")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    """Delete a note by ID.

    Parameters:
        note_id: The ID of the note to delete.

    Returns:
        Empty response with 204 status code on success.

    Raises:
        HTTPException 404 if not found.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return None
