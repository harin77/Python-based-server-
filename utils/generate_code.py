import uuid
import random
import string

def generate_id():
    """Generates a unique string ID (UUID4)."""
    return str(uuid.uuid4())

def generate_join_code(length=6):
    """Generates a random 6-character alphanumeric code for groups."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_user_tag():
    """Generates a 4-digit tag like '1234'."""
    return f"{random.randint(0, 9999):04d}"

def create_handle(username, tag):
    """Creates a handle like 'Username#1234'."""
    return f"{username}#{tag}"