import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import api_key_store as aks  # noqa: E402


class ApiKeyStoreTests(unittest.TestCase):
    def test_resolve_prefers_keyring_over_env(self):
        with patch.object(aks.keyring, "get_password", return_value="keyring-key"), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            self.assertEqual(aks.resolve_api_key(), "keyring-key")

    def test_resolve_falls_back_to_env_when_keyring_empty(self):
        with patch.object(aks.keyring, "get_password", return_value=None), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            self.assertEqual(aks.resolve_api_key(), "env-key")

    def test_resolve_returns_none_when_neither_set(self):
        with patch.object(aks.keyring, "get_password", return_value=None), \
                patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(aks.resolve_api_key())

    def test_set_stored_key_calls_keyring_set_password(self):
        with patch.object(aks.keyring, "set_password") as mock_set:
            aks.set_stored_key("abc123")
            mock_set.assert_called_once_with("cropper", "openai_api_key", "abc123")

    def test_clear_stored_key_calls_delete_password(self):
        with patch.object(aks.keyring, "delete_password") as mock_delete:
            aks.clear_stored_key()
            mock_delete.assert_called_once_with("cropper", "openai_api_key")

    def test_clear_stored_key_swallows_missing_password_error(self):
        with patch.object(aks.keyring, "delete_password",
                           side_effect=aks.PasswordDeleteError()):
            aks.clear_stored_key()  # must not raise

    def test_get_stored_key_returns_none_when_keyring_raises(self):
        with patch.object(aks.keyring, "get_password", side_effect=RuntimeError("no backend")):
            self.assertIsNone(aks.get_stored_key())


if __name__ == "__main__":
    unittest.main()
