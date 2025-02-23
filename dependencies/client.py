from typing import Dict, Optional
import json
import logging
from instagrapi import Client
from fastapi import Depends, HTTPException
from tinydb import TinyDB

db = TinyDB('db.json')
logger = logging.getLogger(__name__)

# Cache for storing client instances
_client_cache: Dict[str, Client] = {}

def get_client() -> Client:
    """Get an authenticated Instagram client
    
    Returns:
        Client: Authenticated Instagram client
        
    Raises:
        HTTPException: If authentication fails
    """
    sessions = db.table('_default').all()
    if not sessions:
        raise HTTPException(status_code=401, detail="No session found")
        
    # Get the most recent session by parsing the settings JSON string
    try:
        latest_session = max(
            sessions,
            key=lambda x: json.loads(x.get('settings', '{}')).get('last_login', 0)
        )
    except Exception as e:
        logger.error(f"Error parsing session data: {e}")
        raise HTTPException(status_code=401, detail="Invalid session data")
    
    sessionid = latest_session.get('sessionid')
    if not sessionid:
        raise HTTPException(status_code=401, detail="No sessionid found")
    
    # Return cached client if available
    if sessionid in _client_cache:
        return _client_cache[sessionid]
    
    # Create and cache new client
    try:
        client = Client()
        client.login_by_sessionid(sessionid)
        _client_cache[sessionid] = client
        return client
    except KeyError as e:
        logger.error(f"Instagram API response missing expected field: {e}")
        if sessionid in _client_cache:
            del _client_cache[sessionid]
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    except Exception as e:
        logger.error(f"Error logging in with sessionid: {e}")
        if sessionid in _client_cache:
            del _client_cache[sessionid]
        raise HTTPException(status_code=401, detail="Authentication failed") 