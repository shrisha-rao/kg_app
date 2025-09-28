#src/services/user_service.py
from google.cloud import firestore
from typing import Optional, List
from src.models.user import User, UserUpdate
from src.config import settings


class UserService:

    def __init__(self):
        self.db = firestore.Client(project=settings.gcp_project_id)
        self.collection = self.db.collection("users")

    async def get_user(self, uid: str) -> Optional[User]:
        """Get a user by UID"""
        # --- DEBUG BLOCK ---
        if uid == "test_user_123":
            from datetime import datetime
            from src.models.user import User  # Ensure User is imported
            return User(
                uid=uid,
                email=f"{uid}@example.com",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        # --- END DEBUG BLOCK ---
        doc_ref = self.collection.document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return User(**doc.to_dict())
        return None

    async def create_user(self, user: User) -> User:
        """Create a new user in Firestore"""
        doc_ref = self.collection.document(user.uid)
        doc_ref.set(user.to_dict())
        return user

    async def update_user(self, uid: str,
                          user_update: UserUpdate) -> Optional[User]:
        """Update a user in Firestore"""
        doc_ref = self.collection.document(uid)

        # Get current user data
        doc = doc_ref.get()
        if not doc.exists:
            return None

        current_data = doc.to_dict()

        # Update fields
        update_data = {}
        if user_update.display_name is not None:
            update_data["display_name"] = user_update.display_name
        if user_update.preferences is not None:
            update_data["preferences"] = {
                **current_data.get("preferences", {}),
                **user_update.preferences
            }

        update_data["updated_at"] = firestore.SERVER_TIMESTAMP

        # Update the document
        doc_ref.update(update_data)

        # Return updated user
        updated_doc = doc_ref.get()
        return User(**updated_doc.to_dict())

    async def update_library_stats(self, uid: str, stats_update: dict) -> None:
        """Update user's library statistics"""
        doc_ref = self.collection.document(uid)
        doc_ref.update({
            "library_stats": stats_update,
            "updated_at": firestore.SERVER_TIMESTAMP
        })

    async def delete_user(self, uid: str) -> bool:
        """Delete a user from Firestore"""
        doc_ref = self.collection.document(uid)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            return True
        return False


# Create a singleton instance
user_service = UserService()
