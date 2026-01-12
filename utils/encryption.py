import bcrypt
import jwt
import datetime
import logging
from chat_server.config import SECRET_KEY, BCRYPT_ROUNDS

def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    Returns the hash as a string for storage.
    """
    try:
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logging.error(f"Hashing error: {e}")
        return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks a plain password against its stored hash.
    Handles encoding to ensure bytes are passed to bcrypt.
    """
    try:
        # bcrypt requires bytes, so we encode both
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logging.error(f"Password verification error: {e}")
        return False

def generate_token(user_id: str) -> str:
    """
    Generates a JWT token for session management.
    Token expires in 7 days.
    """
    try:
        payload = {
            "user_id": user_id,
            # Use timezone-aware UTC to prevent DeprecationWarnings
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    except Exception as e:
        logging.error(f"Token generation error: {e}")
        return ""

def verify_token(token: str) -> str:
    """
    Decodes a JWT token.
    Returns user_id if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        logging.warning("Token expired")
        return None
    except jwt.InvalidTokenError:
        logging.warning("Invalid token")
        return None