from typing import Dict, Optional
from instagrapi import Client
from tinydb import TinyDB

db = TinyDB('db.json')

class ClientStorage:
    def __init__(self):
        self.clients: Dict[str, Client] = {}
    
    def client(self) -> Client:
        """Get a new client instance
        
        Returns:
            Client: New Instagram client
        """
        return Client()
    
    def get(self, sessionid: str) -> Client:
        """Get client by sessionid
        
        Args:
            sessionid: Session ID
            
        Returns:
            Client: Instagram client
        """
        if sessionid not in self.clients:
            cl = self.client()
            cl.login_by_sessionid(sessionid)
            self.clients[sessionid] = cl
        return self.clients[sessionid]
    
    def set(self, client: Client):
        """Set client
        
        Args:
            client: Instagram client
        """
        self.clients[client.sessionid] = client

# Global client storage
client_storage = ClientStorage()

def get_clients() -> ClientStorage:
    """Get client storage
    
    Returns:
        ClientStorage: Client storage instance
    """
    return client_storage
