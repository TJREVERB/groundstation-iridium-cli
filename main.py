import json
from os import path

def secrets_file_exists() -> bool:
    SECRETS_FILE_URL = "credentials.json"
    SECRETS_FILE_ENCRYPTED_URL = "credentials.json.gpg"
    if path.exists(SECRETS_FILE_URL):
        return True
    elif path.exists(SECRETS_FILE_ENCRYPTED_URL):
        return False
    else:
        return False

def get_imei() -> int:
    pass

