from typing import List, Optional
from fastapi import APIRouter, Depends
from instagrapi import Client
from dependencies.client import get_client

router = APIRouter(prefix="", tags=["hashtag"])

@router.get("/v1/hashtag/medias/top/recent/chunk", response_model=List)
async def hashtag_medias_v1_chunk(
    name: str,
    client: Client = Depends(get_client),
    max_id: Optional[str] = None
) -> List:
    """
    Search for hashtags on Instagram.
    
    Args:
        name: Hashtag to search for (without #).
        max_id: Used for pagination.
        
    Returns:
        List: Search results as a list of media items.
    """
    # Remove # if present in name
    name = name.lstrip("#")
    
    # Call Instagram API and get results
    results = client.hashtag_medias_v1_chunk(
        name=name,
        max_id=max_id,
        tab_key="recent"
    )
    
    return results

@router.get("/v1/search/hashtags", response_model=List)
async def get_hashtag_info(
    query: str,
    client: Client = Depends(get_client)
) -> List:
    """
    Return a list of related hashtags.
    
    Args:
        name: Hashtag name (without #).
        
    Returns:
        List[str]: List of related hashtags.
    """
    # Remove # if present
    query = query.lstrip("#")
    
    # Fetch related hashtags from the Instagram API
    related_hashtags = client.search_hashtags(query)

    return related_hashtags