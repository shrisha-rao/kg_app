#src/api/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from src.models.user import UserCreate, UserResponse, UserUpdate
from src.utils.auth import get_current_user, create_custom_token
from src.services.user_service import user_service
import firebase_admin
from firebase_admin import auth as firebase_auth

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/signup",
             response_model=dict,
             status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """
    Create a new user account
    """
    try:
        # Create user in Firebase Authentication
        user = firebase_auth.create_user(email=user_data.email,
                                         password=user_data.password,
                                         display_name=user_data.display_name)

        # Create user in Firestore
        user_model = User(uid=user.uid,
                          email=user_data.email,
                          display_name=user_data.display_name)

        await user_service.create_user(user_model)

        # Create custom token for immediate login
        token = create_custom_token(user.uid)

        return {
            "message": "User created successfully",
            "uid": user.uid,
            "token": token
        }
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}",
        )


@router.post("/login", response_model=dict)
async def login(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Login with Firebase token (handled by client SDK, this validates the token)
    """
    try:
        token = credentials.credentials
        decoded_token = firebase_auth.verify_id_token(token)

        # Check if user exists in Firestore, create if not
        user = await user_service.get_user(decoded_token["uid"])
        if not user:
            # Create user in Firestore if they don't exist
            firebase_user = firebase_auth.get_user(decoded_token["uid"])
            user_model = User.from_firebase_user({
                "uid":
                firebase_user.uid,
                "email":
                firebase_user.email,
                "displayName":
                firebase_user.display_name,
                "photoURL":
                firebase_user.photo_url,
                "emailVerified":
                firebase_user.email_verified,
                "disabled":
                firebase_user.disabled
            })
            await user_service.create_user(user_model)

        return {
            "message": "Login successful",
            "uid": decoded_token["uid"],
            "token": token
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user information
    """
    user = await user_service.get_user(current_user["uid"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(user_update: UserUpdate,
                    current_user: dict = Depends(get_current_user)):
    """
    Update current user information
    """
    updated_user = await user_service.update_user(current_user["uid"],
                                                  user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return updated_user


@router.post("/refresh", response_model=dict)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refresh authentication token
    """
    try:
        token = create_custom_token(current_user["uid"])
        return {"message": "Token refreshed", "token": token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}",
        )


@router.post("/logout", response_model=dict)
async def logout():
    """
    Logout endpoint (client should remove token from storage)
    """
    return {"message": "Logout successful"}
