import json
import os
import shutil
import threading
from datetime import datetime
from chat_server.config import BACKUP_DIR

class FileIO:
    """
    Handles thread-safe JSON file operations and automatic backups.
    Instantiated per file to manage specific locks.
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.lock = threading.Lock()
        
        # Ensure directories exist immediately upon initialization
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

    def read_json(self):
        """
        Loads JSON data safely. 
        Returns empty dict/list if file doesn't exist or is corrupted.
        """
        with self.lock:
            if not os.path.exists(self.filepath):
                return {}
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # Return empty dict on corruption or read error to prevent crashes
                return {}

    def write_json(self, data):
        """
        Saves JSON data and creates a backup copy.
        """
        with self.lock:
            try:
                # 1. Create Backup (if file exists)
                if os.path.exists(self.filepath):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.basename(self.filepath)
                    backup_path = os.path.join(BACKUP_DIR, f"{filename}_{timestamp}.bak")
                    
                    # Copy file to backup folder
                    shutil.copy2(self.filepath, backup_path)
                    
                    # Optional: Prune old backups (keep last 5)
                    self._prune_backups(filename)

                # 2. Write New Data
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"Error writing/backing up {self.filepath}: {e}")
                return False

    def _prune_backups(self, filename):
        """
        Helper to keep only the 5 most recent backups for this file.
        """
        try:
            # Find all backups for this specific file
            all_backups = [
                os.path.join(BACKUP_DIR, f) 
                for f in os.listdir(BACKUP_DIR) 
                if f.startswith(filename) and f.endswith(".bak")
            ]
            
            # Sort by modification time (newest last)
            all_backups.sort(key=os.path.getmtime)
            
            # Remove old ones if we have more than 5
            while len(all_backups) > 5:
                oldest = all_backups.pop(0)
                os.remove(oldest)
        except Exception:
            # Pruning failure shouldn't stop the main write operation
            pass