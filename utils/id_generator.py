import random
import string
import time

def generate_join_code(length=6):
    """Generates a random 6-character alphanumeric code for groups."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_user_tag():
    """Generates a 4-digit tag like 1024."""
    return "".join(random.choices(string.digits, k=4))

def generate_id():
    """Generates a unique internal ID based on timestamp."""
    # Simple timestamp + random suffix based ID
    timestamp = int(time.time() * 1000)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{timestamp}{suffix}"

def create_handle(username, tag):
    """Creates a display handle like User#1234."""
    return f"{username}#{tag}"