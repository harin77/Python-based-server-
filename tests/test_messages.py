import unittest
import os
import json
import shutil
from unittest.mock import MagicMock, AsyncMock, patch

# Adjust import paths to find the module
import sys
sys.path.append(os.getcwd())

from chat_server.handlers.message_handler import MessageHandler
from chat_server.utils.file_io import FileIO

# Define a temporary path for testing
TEST_DB_DIR = os.path.join(os.getcwd(), "chat_server", "tests", "temp_db")
TEST_MESSAGES_DB = os.path.join(TEST_DB_DIR, "messages.json")
TEST_GROUPS_DB = os.path.join(TEST_DB_DIR, "groups.json")

class MockClientManager:
    """Mocks the ClientManager."""
    def __init__(self):
        self.send_personal_message = AsyncMock()
        # Mock connection map to simulate logged-in users
        self.connection_map = {}

class TestMessageHandler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Runs before each test: Setup temp DB and Mocks."""
        # 1. Setup temporary test directory and empty JSON files
        os.makedirs(TEST_DB_DIR, exist_ok=True)
        with open(TEST_MESSAGES_DB, 'w') as f:
            json.dump({}, f)
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump({}, f)

        # 2. Mock Client Manager
        self.mock_client_manager = MockClientManager()

        # 3. Initialize Handler
        # We patch the config paths to point to our test DBs
        with patch("chat_server.handlers.message_handler.MESSAGES_DB", TEST_MESSAGES_DB), \
             patch("chat_server.handlers.message_handler.GROUPS_DB", TEST_GROUPS_DB):
            
            self.message_handler = MessageHandler(self.mock_client_manager)
            # Force the IO instances to use our test DBs
            self.message_handler.messages_io = FileIO(TEST_MESSAGES_DB)
            self.message_handler.groups_io = FileIO(TEST_GROUPS_DB)

        # 4. Mock Websocket and authorize a user
        self.mock_ws = AsyncMock()
        self.mock_ws.send = AsyncMock()
        
        # Simulate User A is connected via this socket
        self.sender_id = "user_A"
        self.mock_client_manager.connection_map[self.mock_ws] = self.sender_id

    def tearDown(self):
        """Runs after each test: Cleanup temp files."""
        if os.path.exists(TEST_DB_DIR):
            shutil.rmtree(TEST_DB_DIR)

    async def test_send_private_message(self):
        """Test sending a 1-on-1 message."""
        target_id = "user_B"
        payload = {
            "to": target_id,
            "content": "Hello World",
            "msg_type": "text"
        }

        await self.message_handler.handle_send(self.mock_ws, payload)

        # 1. Verify Message Saved to DB
        with open(TEST_MESSAGES_DB, 'r') as f:
            db_data = json.load(f)
        
        # Key should be sorted: user_A + user_B -> "user_A_user_B"
        chat_key = "_".join(sorted([self.sender_id, target_id]))
        self.assertIn(chat_key, db_data)
        
        message = db_data[chat_key][0]
        self.assertEqual(message["content"], "Hello World")
        self.assertEqual(message["sender_id"], self.sender_id)
        self.assertFalse(message["is_deleted"])

        # 2. Verify Broadcast (Target AND Sender should receive it)
        # We expect 2 calls to send_personal_message
        self.assertEqual(self.mock_client_manager.send_personal_message.call_count, 2)
        
        # Check logic: it calls send_personal_message(payload, uid)
        call_args_list = self.mock_client_manager.send_personal_message.call_args_list
        recipients = [call.args[1] for call in call_args_list]
        self.assertIn(target_id, recipients)
        self.assertIn(self.sender_id, recipients)

    async def test_send_group_message(self):
        """Test sending a message to a group."""
        group_id = "group_123"
        member_id = "user_C"
        
        # 1. Pre-seed Groups DB
        group_data = {
            group_id: {
                "id": group_id,
                "members": [self.sender_id, member_id]
            }
        }
        with open(TEST_GROUPS_DB, 'w') as f:
            json.dump(group_data, f)

        # 2. Send Message
        payload = {
            "to": group_id,
            "content": "Hi Group!",
            "msg_type": "text"
        }
        await self.message_handler.handle_send(self.mock_ws, payload)

        # 3. Verify Message Saved under Group ID
        with open(TEST_MESSAGES_DB, 'r') as f:
            db_data = json.load(f)
        
        self.assertIn(group_id, db_data)
        self.assertEqual(db_data[group_id][0]["content"], "Hi Group!")

        # 4. Verify Broadcast to all members
        call_args_list = self.mock_client_manager.send_personal_message.call_args_list
        recipients = [call.args[1] for call in call_args_list]
        
        self.assertIn(member_id, recipients)
        self.assertIn(self.sender_id, recipients)

    async def test_delete_message(self):
        """Test deleting a message."""
        target_id = "user_B"
        chat_key = "_".join(sorted([self.sender_id, target_id]))
        message_id = "msg_123"

        # 1. Pre-seed DB with a message
        initial_msg = {
            "id": message_id,
            "sender_id": self.sender_id,
            "content": "Original Content",
            "type": "text",
            "is_deleted": False
        }
        with open(TEST_MESSAGES_DB, 'w') as f:
            json.dump({chat_key: [initial_msg]}, f)

        # 2. Send Delete Request
        payload = {
            "chat_id": target_id,
            "message_id": message_id
        }
        await self.message_handler.handle_delete(self.mock_ws, payload)

        # 3. Verify DB Update
        with open(TEST_MESSAGES_DB, 'r') as f:
            db_data = json.load(f)
        
        updated_msg = db_data[chat_key][0]
        self.assertTrue(updated_msg["is_deleted"])
        self.assertEqual(updated_msg["type"], "deleted")
        self.assertIn("deleted", updated_msg["content"]) # Content should be masked

        # 4. Verify Broadcast
        self.mock_client_manager.send_personal_message.assert_called()

    async def test_typing_indicator(self):
        """Test typing status broadcast."""
        target_id = "user_B"
        payload = {
            "to": target_id,
            "is_typing": True
        }

        await self.message_handler.handle_typing(self.mock_ws, payload)

        # Verify broadcast is sent ONLY to the target, NOT echoed to sender
        self.mock_client_manager.send_personal_message.assert_called_once()
        args, _ = self.mock_client_manager.send_personal_message.call_args
        
        sent_payload = args[0]
        recipient = args[1]
        
        self.assertEqual(recipient, target_id)
        self.assertEqual(sent_payload["data"]["from"], self.sender_id)
        self.assertTrue(sent_payload["data"]["is_typing"])

if __name__ == "__main__":
    unittest.main()