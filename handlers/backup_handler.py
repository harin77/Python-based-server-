import shutil
import os
import base64
import json
import time
from chat_server.utils.response import success, error
from chat_server.config import DB_DIR, BACKUP_DIR

class BackupHandler:
    def __init__(self, client_manager):
        self.client_manager = client_manager

    async def handle_backup_request(self, websocket, user_id):
        """
        Zips the database directory and sends it as a Base64 string.
        
        Action: 'request_backup'
        Payload: None required (triggered by user_id)
        """
        if not user_id:
            return await websocket.send(json.dumps(error("auth", "Authentication required")))

        try:
            # 1. Setup Paths
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = int(time.time())
            backup_base_name = os.path.join(BACKUP_DIR, f"backup_{user_id}_{timestamp}")
            
            # 2. Create ZIP Archive
            # shutil.make_archive adds the format extension automatically (e.g., .zip)
            archive_path = shutil.make_archive(
                base_name=backup_base_name, 
                format='zip', 
                root_dir=DB_DIR
            )
            
            # 3. Read and Encode
            if os.path.exists(archive_path):
                with open(archive_path, "rb") as f:
                    encoded_data = base64.b64encode(f.read()).decode('utf-8')
                
                # 4. Send Response
                await websocket.send(json.dumps(success("backup_ready", {
                    "file_name": f"chat_backup_{timestamp}.zip",
                    "file_data": encoded_data
                })))
                
                # 5. Cleanup (Delete the temporary zip file)
                try:
                    os.remove(archive_path)
                except OSError as e:
                    print(f"Error deleting backup file {archive_path}: {e}")
            else:
                await websocket.send(json.dumps(error("backup", "Backup generation failed")))
                
        except Exception as e:
            print(f"Backup Error: {e}")
            await websocket.send(json.dumps(error("backup", f"Server error: {str(e)}")))