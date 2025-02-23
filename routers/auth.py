import json
from unittest.mock import patch
from typing import Optional, Dict
from fastapi import APIRouter, Depends, Form, HTTPException
from dependencies import ClientStorage, get_clients
from pydantic import BaseModel
from instagrapi import Client
from tinydb import TinyDB
from datetime import datetime

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)

db = TinyDB('db.json')

class LoginRequest(BaseModel):
    username: str
    password: str

class SessionLoginRequest(BaseModel):
    sessionid: str

@router.post("/login")
async def login(request: LoginRequest):
    """Login to Instagram using username and password
    
    Args:
        request: Login credentials
        
    Returns:
        dict: Session information
    """
    try:
        client = Client()
        client.login(request.username, request.password)
        
        # Get the session data
        session_data = {
            "sessionid": client.sessionid,
            "settings": json.dumps({
                "last_login": datetime.now().timestamp(),
                "user_id": client.user_id,
                "username": request.username
            })
        }
        
        # Save to database
        db.table('_default').insert(session_data)
        
        return {
            "status": "ok",
            "sessionid": client.sessionid
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/login/by_sessionid")
async def login_by_sessionid(request: SessionLoginRequest):
    """Login to Instagram using an existing session ID
    
    Args:
        request: Session ID
        
    Returns:
        dict: Session information
    """
    try:
        client = Client()
        client.login_by_sessionid(request.sessionid)
        
        # Get the session data
        session_data = {
            "sessionid": request.sessionid,
            "settings": json.dumps({
                "last_login": datetime.now().timestamp(),
                "user_id": client.user_id,
                "username": client.username
            })
        }
        
        # Save to database
        db.table('_default').insert(session_data)
        
        return {
            "status": "ok",
            "sessionid": request.sessionid
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout(sessionid: str):
    """Logout and remove session from database
    
    Args:
        sessionid: Session ID to logout
        
    Returns:
        dict: Status message
    """
    try:
        # Remove from database
        db.table('_default').remove(
            lambda x: x.get('sessionid') == sessionid
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login_by_sessionid")
async def auth_login_by_sessionid(sessionid: str = Form(...),
                                  clients: ClientStorage = Depends(get_clients)) -> str:
    """Login by sessionid
    """
    cl = clients.client()
    result = cl.login_by_sessionid(sessionid)
    if result:
        clients.set(cl)
        return cl.sessionid
    return result


@router.post("/relogin")
async def auth_relogin(sessionid: str = Form(...),
                       clients: ClientStorage = Depends(get_clients)) -> str:
    """Relogin by username and password (with clean cookies)
    """
    cl = clients.get(sessionid)
    result = cl.relogin()
    return result


@router.get("/settings/get")
async def settings_get(sessionid: str,
                       clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get client's settings
    """
    cl = clients.get(sessionid)
    return cl.get_settings()


@router.post("/settings/set")
async def settings_set(settings: str = Form(...),
                       sessionid: Optional[str] = Form(""),
                       clients: ClientStorage = Depends(get_clients)) -> str:
    """Set client's settings
    """
    if sessionid != "":
        cl = clients.get(sessionid)
    else:
        cl = clients.client()
    cl.set_settings(json.loads(settings))
    cl.expose()
    clients.set(cl)
    return cl.sessionid


@router.get("/timeline_feed")
async def timeline_feed(sessionid: str,
                        clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get your timeline feed
    """
    cl = clients.get(sessionid)
    return cl.get_timeline_feed()
