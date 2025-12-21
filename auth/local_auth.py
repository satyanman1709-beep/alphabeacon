import hashlib
from auth.config import LOCAL_USERNAME, LOCAL_PASSWORD


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


HASHED_LOCAL_PASSWORD = hash_password(LOCAL_PASSWORD)


def verify_local_login(username, password):
    """
    Validates username + password for local login.
    """
    if username != LOCAL_USERNAME:
        return False

    return hash_password(password) == HASHED_LOCAL_PASSWORD
