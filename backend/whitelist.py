import firebase_admin
from firebase_admin import credentials, auth
import argparse

def whitelist_user(uid: str) -> None:
    """
    Whitelist a user by setting their custom claims in Firebase Auth.
    
    Args:
        uid: The user ID to whitelist
    """
    try:
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            from firebase.firebase_credentials import get_firebase_credentials
            cred = credentials.Certificate(get_firebase_credentials())
            firebase_admin.initialize_app(cred)

        # Set the custom claim
        auth.set_custom_user_claims(uid, {'whitelisted': True})
        print(f"Success: User {uid} has been whitelisted.")
    
    except Exception as e:
        print(f"Error: Failed to whitelist user. {str(e)}")

def unwhitelist_user(uid: str) -> None:
    """
    Remove whitelist status from a user by setting their custom claims in Firebase Auth.
    
    Args:
        uid: The user ID to unwhitelist
    """
    try:
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            from firebase.firebase_credentials import get_firebase_credentials
            cred = credentials.Certificate(get_firebase_credentials())
            firebase_admin.initialize_app(cred)

        # Remove the custom claim by setting it to False
        auth.set_custom_user_claims(uid, {'whitelisted': False}) 
        print(f"Success: User {uid} has been unwhitelisted.")
    
    except Exception as e:
        print(f"Error: Failed to unwhitelist user. {str(e)}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Whitelist or unwhitelist a user in Firebase')
    parser.add_argument('--uid', required=True, help='The user ID to modify')
    parser.add_argument('--action', required=True, choices=['whitelist', 'unwhitelist'], 
                      help='Action to perform')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call the appropriate function based on action
    if args.action == 'whitelist':
        whitelist_user(args.uid)
    else:
        unwhitelist_user(args.uid)

if __name__ == "__main__":
    main()