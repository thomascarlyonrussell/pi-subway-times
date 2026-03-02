import json
import os
import pathlib
import sys
import unittest
from unittest import mock

PYTHON_DIR = pathlib.Path(__file__).resolve().parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

os.environ.setdefault("SUBWAY_SETUP_PIN", "123456")
os.environ.setdefault("WEB_CONFIG_SECRET_KEY", "test-secret")

workspace_tmp_root = pathlib.Path(__file__).resolve().parent.parent / ".tmp"
workspace_tmp_root.mkdir(parents=True, exist_ok=True)
temp_dir = workspace_tmp_root / "subway-wifi-security"
temp_dir.mkdir(parents=True, exist_ok=True)
os.environ["MATRIX_CONFIG_PATH"] = str(temp_dir / "matrix_config.json")
os.environ["MATRIX_CONFIG_DEFAULT_PATH"] = str(
    pathlib.Path(__file__).resolve().parent.parent / "setup" / "matrix_config_default.json"
)

from config import DEFAULT_CONFIG  # noqa: E402
import web_config  # noqa: E402


class WifiOnboardingSecurityValidation(unittest.TestCase):
    def setUp(self):
        self.client = web_config.app.test_client()
        self.config_path = pathlib.Path(os.environ["MATRIX_CONFIG_PATH"])
        self.config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")

    def test_unauthenticated_mutation_is_denied(self):
        response = self.client.post("/", data={"ssid": "test-network"})
        self.assertEqual(response.status_code, 401)

    def test_authenticated_mutation_allowed_and_password_encrypted(self):
        login = self.client.post("/auth/login", json={"pin": "123456"})
        self.assertEqual(login.status_code, 200)

        with mock.patch("web_config.apply_runtime_changes", return_value=False):
            response = self.client.post(
                "/",
                data={"ssid": "test-network", "password": "SuperSecretPassword"},
            )
        self.assertEqual(response.status_code, 200)

        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["wifi"]["ssid"], "test-network")
        self.assertNotEqual(saved["wifi"]["password"], "SuperSecretPassword")
        self.assertTrue(saved["wifi"]["password"].startswith("enc:"))

    def test_log_redaction_masks_password_and_token_fields(self):
        payload = {
            "ssid": "dev-net",
            "password": "plaintext",
            "token": "abc",
            "nested": {"pin": "111111", "other": "ok"},
        }
        redacted = web_config._redact_sensitive(payload)  # pylint: disable=protected-access
        self.assertEqual(redacted["password"], "***REDACTED***")
        self.assertEqual(redacted["token"], "***REDACTED***")
        self.assertEqual(redacted["nested"]["pin"], "***REDACTED***")
        self.assertEqual(redacted["nested"]["other"], "ok")


if __name__ == "__main__":
    unittest.main()
