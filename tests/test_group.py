import unittest
import os
import json
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

# Adjust import paths to find the module
import sys
sys.path.append(os.getcwd())

from chat_server.handlers.group_handler import GroupHandler
from chat_server.utils.file_io import FileIO

# Define a temporary path for testing
TEST_DB_DIR = os.path.join(os.getcwd(), "chat_server", "tests", "temp_db")
TEST_GROUPS_DB = os.path.join(TEST_DB_DIR, "groups.json")

class MockClientManager:
    """Mocks the ClientManager."""
    def __init__(self):
        self.send_personal_message = AsyncMock()
        # Mock connection map required by GroupHandler
        self.ws_to_user = {}

class TestGroupHandler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Runs before each test: Setup temp DB and Mocks."""
        # 1. Setup temporary test directory and empty JSON
        os.makedirs(TEST_DB_DIR, exist_ok=True)
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump({}, f)

        # 2. Mock Client Manager
        self.mock_client_manager = MockClientManager()

        # 3. Initialize Handler
        with patch("chat_server.handlers.group_handler.GROUPS_DB", TEST_GROUPS_DB):
            self.group_handler = GroupHandler(self.mock_client_manager)
            # Force the IO to use our test DB
            self.group_handler.groups_io = FileIO(TEST_GROUPS_DB)

        # 4. Mock Websocket
        self.mock_ws = AsyncMock()
        self.mock_ws.send = AsyncMock()

    def tearDown(self):
        """Runs after each test: Cleanup temp files."""
        if os.path.exists(TEST_DB_DIR):
            shutil.rmtree(TEST_DB_DIR)

    async def test_create_group(self):
        """Test creating a new group."""
        owner_id = "user_owner_123"
        
        # MOCK SETUP: Map the socket to the owner_id
        self.mock_client_manager.ws_to_user[self.mock_ws] = owner_id
        
        payload = {
            "action": "create_group",
            "name": "Study Group A"
        }

        await self.group_handler.handle_create(self.mock_ws, payload)

        # 1. Verify Response sent to socket
        self.mock_ws.send.assert_called_once()
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["type"], "create_group")
        self.assertEqual(response["data"]["name"], "Study Group A")
        self.assertEqual(response["data"]["owner_id"], owner_id)
        self.assertTrue(len(response["data"]["join_code"]) == 6)

        # 2. Verify Database update
        with open(TEST_GROUPS_DB, 'r') as f:
            db_data = json.load(f)
        
        group = list(db_data.values())[0]
        self.assertEqual(group["name"], "Study Group A")
        self.assertIn(owner_id, group["members"])
        # Verify role is correct in the new dict structure
        self.assertEqual(group["members"][owner_id]["role"], "owner")

    async def test_join_group_success(self):
        """Test joining a group with a valid code."""
        # 1. Pre-seed DB with a group
        owner_id = "user_owner_123"
        join_code = "ABC123"
        group_id = "group_test_id"
        
        initial_db = {
            group_id: {
                "id": group_id,
                "name": "Test Group",
                "owner_id": owner_id,
                "join_code": join_code,
                "members": {
                    owner_id: {"role": "owner", "muted": False}
                }
            }
        }
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump(initial_db, f)

        # 2. Attempt Join
        new_user_id = "user_new_456"
        
        # MOCK SETUP: Map socket to the NEW user
        self.mock_client_manager.ws_to_user[self.mock_ws] = new_user_id
        
        payload = {
            "action": "join_group",
            "join_code": join_code
        }
        
        await self.group_handler.handle_join(self.mock_ws, payload)

        # 3. Verify Response
        self.mock_ws.send.assert_called_once()
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["type"], "join_group")
        self.assertEqual(response["data"]["group_id"], group_id)

        # 4. Verify DB updated with new member
        with open(TEST_GROUPS_DB, 'r') as f:
            db_data = json.load(f)
            members = db_data[group_id]["members"]
            self.assertIn(new_user_id, members)
            self.assertEqual(members[new_user_id]["role"], "member")

    async def test_join_group_invalid_code(self):
        """Test joining with a wrong code."""
        # 1. Pre-seed DB
        initial_db = {
            "g1": {"id": "g1", "join_code": "REALCODE", "members": {}}
        }
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump(initial_db, f)

        # MOCK SETUP
        self.mock_client_manager.ws_to_user[self.mock_ws] = "user_1"

        # 2. Attempt Join
        payload = {
            "action": "join_group",
            "join_code": "WRONGCODE"
        }
        
        await self.group_handler.handle_join(self.mock_ws, payload)

        # 3. Verify Error
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])
        
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Invalid Join Code")

    async def test_join_group_already_member(self):
        """Test joining a group user is already in."""
        user_existing = "user_existing"
        
        # 1. Pre-seed DB
        initial_db = {
            "g1": {
                "id": "g1", 
                "join_code": "CODE", 
                "members": {
                    user_existing: {"role": "member"}
                }
            }
        }
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump(initial_db, f)

        # MOCK SETUP: Map socket to existing user
        self.mock_client_manager.ws_to_user[self.mock_ws] = user_existing

        # 2. Attempt Join
        payload = {
            "action": "join_group",
            "join_code": "CODE"
        }
        
        await self.group_handler.handle_join(self.mock_ws, payload)

        # 3. Verify Error
        args, _ = self.mock_ws.send.call_args
        response = json.loads(args[0])
        
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Already a member")

if __name__ == "__main__":
    unittest.main()