#src/models/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud import firestore


class User(BaseModel):
    uid: str
    email: EmailStr
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    email_verified: bool = False
    disabled: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    roles: List[str] = ["researcher"]
    preferences: Dict[str, Any] = {}
    library_stats: Dict[str, int] = {
        "paper_count": 0,
        "public_paper_count": 0,
        "private_paper_count": 0
    }

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_firebase_user(cls, firebase_user: dict):
        """Create a User from Firebase user data"""
        return cls(
            uid=firebase_user["uid"],
            email=firebase_user["email"],
            display_name=firebase_user.get("displayName"),
            photo_url=firebase_user.get("photoURL"),
            email_verified=firebase_user.get("emailVerified", False),
            disabled=firebase_user.get("disabled", False),
        )

    def to_dict(self):
        """Convert User to dictionary for Firestore"""
        return {
            "uid": self.uid,
            "email": self.email,
            "display_name": self.display_name,
            "photo_url": self.photo_url,
            "email_verified": self.email_verified,
            "disabled": self.disabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "roles": self.roles,
            "preferences": self.preferences,
            "library_stats": self.library_stats
        }


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    uid: str
    email: EmailStr
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    roles: List[str]
    preferences: Dict[str, Any]
    library_stats: Dict[str, int]
    created_at: datetime
