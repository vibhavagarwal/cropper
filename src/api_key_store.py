"""OS-keyring backed storage for the OpenAI API key, with the environment
variable as a fallback so the pre-existing OPENAI_API_KEY mechanism keeps
working unchanged."""
import os

import keyring
from keyring.errors import PasswordDeleteError

_SERVICE = "cropper"
_USERNAME = "openai_api_key"


def get_stored_key() -> str:
    try:
        return keyring.get_password(_SERVICE, _USERNAME)
    except Exception:  # noqa: BLE001 - no keyring backend must not crash the app
        return None


def set_stored_key(value: str) -> None:
    keyring.set_password(_SERVICE, _USERNAME, value)


def clear_stored_key() -> None:
    try:
        keyring.delete_password(_SERVICE, _USERNAME)
    except PasswordDeleteError:
        pass


def resolve_api_key():
    key = get_stored_key()
    if key:
        return key
    return os.environ.get("OPENAI_API_KEY")
