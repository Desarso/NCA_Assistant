from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File
from firebase_admin import auth, storage
from helpers.Firebase_helpers import Token
from fastapi.security import (
    OAuth2PasswordRequestForm,
)
import uuid
from models.general import UserCredentials

user_router = APIRouter(prefix="/users")



@user_router.post("/auth/login", response_model=Token, tags=["authentication"])
async def login_for_access_token(credentials: UserCredentials):
    """
    Login with email/password to get a Firebase token for API access

    This endpoint is primarily for testing in Swagger UI.
    """
    try:
        # Sign in with Firebase Auth
        user = auth.get_user_by_email(credentials.email)

        # Create a custom token
        custom_token = auth.create_custom_token(user.uid)

        # In a real application, you would exchange this for an ID token
        # Here we're using it directly for simplicity in Swagger UI testing

        return {
            "access_token": custom_token.decode("utf-8")
            if isinstance(custom_token, bytes)
            else custom_token,
            "token_type": "bearer",
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@user_router.post("/auth/token", response_model=Token, tags=["authentication"])
async def login_oauth(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint for Swagger UI
    """
    try:
        # Sign in with Firebase Auth
        user = auth.get_user_by_email(
            form_data.username
        )  # Using username field for email

        # Create a custom token
        custom_token = auth.create_custom_token(user.uid)

        return {
            "access_token": custom_token.decode("utf-8")
            if isinstance(custom_token, bytes)
            else custom_token,
            "token_type": "bearer",
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@user_router.get("/auth/me", response_model=dict, tags=["authentication"])
async def get_current_user_info(request: Request):

    current_user = request.state.user
    
    """
    Return information about the currently authenticated user
    """
    return {
        "status": "success",
        "user": {
            "uid": current_user.uid,
            "email": current_user.email,
            "whitelisted": current_user.whitelisted,
        },
    }


@user_router.post("/profile/picture", response_model=dict, tags=["user"])
async def upload_profile_picture(
    file: UploadFile = File(...),
    request: Request = None
):
    """
    Upload a profile picture for the current user
    """
    try:
        # Get current user
        current_user = request.state.user
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
            
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1]
        filename = f"profile_pictures/{current_user.uid}/{uuid.uuid4()}.{file_extension}"
        
        # Get storage bucket
        bucket = storage.bucket()
        blob = bucket.blob(filename)

        
        # Upload file
        try:
            blob.upload_from_string(
                file_content,
                content_type=file.content_type
            )
        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload profile picture: {str(e)}"
            )

        
        # Make the file publicly accessible
        blob.make_public()

        print("made it here 3")
        
        # Get the public URL
        public_url = blob.public_url
        
        # Update user's profile picture URL in Firebase Auth
        auth.update_user(
            current_user.uid,
            photo_url=public_url
        )
        
        return {
            "status": "success",
            "message": "Profile picture uploaded successfully",
            "photo_url": public_url
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload profile picture: {str(e)}"
        )


