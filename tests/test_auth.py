import unittest
import os
import json
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

# Adjust import paths to find the module
import sys
sys.path.append(os.getcwd())

from chat_server.handlers.auth_handler import AuthHandler
from chat_server.utils.file_io import FileIO

# Define a temporary path for testing
TEST_DB_DIR = os.path.join(os.getcwd(), "chat_server", "tests", "temp_db")
TEST_USERS_DB = os.path.join(TEST_DB_DIR, "users.json")

class MockClientManager:
    """Mocks the ClientManager to intercept connection calls."""
    def __init__(self):
        self.connect = AsyncMock()

class TestAuthHandler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Runs before each test: Setup temp DB and Mocks."""
        # 1. Setup temporary test directory and empty JSON
        os.makedirs(TEST_DB_DIR, exist_ok=True)
        with open(TEST_USERS_DB, 'w') as f:
            json.dump({}, f)

        # 2. Mock Client Manager
        self.mock_client_manager = MockClientManager()

        # 3. Initialize Handler
        # We assume the handler will use the path we force-feed it via patch, 
        # or we manually overwrite the io instance after init.
        with patch("chat_server.handlers.auth_handler.USERS_DB", TEST_USERS_DB):
            self.auth_handler = AuthHandler(self.mock_client_manager)
            # Force the IO to use our test DB (double safety)
            self.auth_handler.users_io = FileIO(TEST_USERS_DB)

        # 4. Mock Websocket
        self.mock_ws = AsyncMock()
        self.mock_ws.send = AsyncMock()

    def tearDown(self):
        """Runs after each test: Cleanup temp files."""
        if os.path.exists(TEST_DB_DIR):
            shutil.rmtree(TEST_DB_DIR)

    async def test_register_success(self):
        """Test legitimate user registration."""
        payload = {
            "username": "TestUser",
            "password": "securepassword123"
        }

        await self.auth_handler.handle_register(self.mock_ws, payload)

        # 1. Verify Response sent to socket
        self.mock_ws.send.assert_called_once()
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["type"], "register")
        self.assertEqual(response["data"]["username"], "TestUser")
        self.assertTrue("token" in response["data"])
        self.assertFalse("password" in response["data"]) # Password should never be returned

        # 2. Verify Database update
        with open(TEST_USERS_DB, 'r') as f:
            db_data = json.load(f)
        
        user = list(db_data.values())[0]
        self.assertEqual(user["username"], "TestUser")
        self.assertNotEqual(user["password"], "securepassword123") # Should be hashed

    async def test_register_missing_fields(self):
        """Test registration with missing password."""
        payload = {"username": "NoPassUser"}
        
        await self.auth_handler.handle_register(self.mock_ws, payload)
        
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])
        
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Missing fields")

    async def test_login_success(self):
        """Test logging in with correct credentials."""
        # Register first
        reg_payload = {"username": "LoginUser", "password": "mypassword"}
        await self.auth_handler.handle_register(self.mock_ws, reg_payload)
        
        # Reset mock to clear the registration call
        self.mock_ws.send.reset_mock()
        
        # Get the generated handle from the DB
        with open(TEST_USERS_DB, 'r') as f:
            db_data = json.load(f)
            user_handle = list(db_data.values())[0]["handle"]

        # Attempt Login
        login_payload = {
            "handle": user_handle,
            "password": "mypassword",
            "fcm_token": "new_fcm_token"
        }
        
        await self.auth_handler.handle_login(self.mock_ws, login_payload)

        # Verify Response
        self.mock_ws.send.assert_called_once()
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["type"], "login")
        self.assertEqual(response["data"]["handle"], user_handle)
        
        # Verify FCM Token Update
        with open(TEST_USERS_DB, 'r') as f:
            db_data = json.load(f)
            user = list(db_data.values())[0]
            self.assertEqual(user["fcm_token"], "new_fcm_token")

    async def test_login_failure(self):
        """Test logging in with wrong password."""
        # Register first
        reg_payload = {"username": "BadPassUser", "password": "correct"}
        await self.auth_handler.handle_register(self.mock_ws, reg_payload)
        self.mock_ws.send.reset_mock()
        
        with open(TEST_USERS_DB, 'r') as f:
            db_data = json.load(f)
            user_handle = list(db_data.values())[0]["handle"]

        # Attempt Login with wrong password
        login_payload = {
            "handle": user_handle,
            "password": "wrongpassword"
        }
        
        await self.auth_handler.handle_login(self.mock_ws, login_payload)
        
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])
        
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Invalid credentials")

if __name__ == "__main__":
    unittest.main()