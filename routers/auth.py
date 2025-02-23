import json
from unittest.mock import patch
from typing import Optional, Dict, Union
from fastapi import APIRouter, Depends, Form, HTTPException, status
from dependencies import ClientStorage, get_clients
from pydantic import BaseModel
from instagrapi import Client
from tinydb import TinyDB
from datetime import datetime
from instagrapi.exceptions import ClientLoginRequired, ClientError, ClientConnectionError
import asyncio

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

class SessionLogoutRequest(BaseModel):
    sessionid: str

class LoginResponse(BaseModel):
    status: str
    sessionid: str
    error: Optional[str] = None

async def _try_login(client: Client, username: str, password: str, max_retries: int = 2) -> Union[dict, Exception]:
    """Try to login with retries
    
    Args:
        client: Instagram client
        username: Instagram username
        password: Instagram password
        max_retries: Maximum number of retry attempts
        
    Returns:
        dict: Session information on success
        Exception: Error on failure
    """
    retry_count = 0
    while retry_count <= max_retries:
        try:
            # Use asyncio.wait_for to implement timeout
            await asyncio.wait_for(
                asyncio.to_thread(client.login, username, password),
                timeout=30.0  # 30 seconds timeout
            )
            
            return {
                "sessionid": client.sessionid,
                "settings": json.dumps({
                    "last_login": datetime.now().timestamp(),
                    "user_id": client.user_id,
                    "username": username
                })
            }
        except asyncio.TimeoutError:
            retry_count += 1
            if retry_count > max_retries:
                return asyncio.TimeoutError("Login request timed out after multiple retries")
            await asyncio.sleep(1)  # Wait before retry
        except ClientConnectionError as e:
            retry_count += 1
            if retry_count > max_retries:
                return e
            await asyncio.sleep(1)  # Wait before retry
        except Exception as e:
            return e

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login to Instagram using username and password
    
    Args:
        request: Login credentials
        
    Returns:
        LoginResponse: Session information and status
    """
    client = Client()
    result = await _try_login(client, request.username, request.password)
    
    if isinstance(result, Exception):
        error_msg = str(result)
        status_code = status.HTTP_401_UNAUTHORIZED
        
        if isinstance(result, ClientConnectionError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_msg = "Connection to Instagram failed. Please try again later."
        elif isinstance(result, asyncio.TimeoutError):
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            error_msg = "Login request timed out. Please try again."
            
        raise HTTPException(
            status_code=status_code,
            detail=error_msg
        )
    
    # Save to database
    db.table('_default').insert(result)
    
    return LoginResponse(
        status="ok",
        sessionid=result["sessionid"]
    )

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
async def logout(request: SessionLogoutRequest):
    """Logout and remove session from database
    
    Args:
        sessionid: Session ID to logout
        
    Returns:
        dict: Status message
    """
    try:
        # Remove from database
        db.table('_default').remove(
            lambda x: x.get('sessionid') == request.sessionid
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
