import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.schemas import WebSource

async def search_serpapi(query: str, num_results: int = 3) -> Dict[str, Any]:
    """
    Queries SerpApi Google Search engine.
    Returns:
        {
            "success": bool,
            "sources": List[WebSource],
            "search_query": str,
            "message": Optional[str]
        }
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "success": False,
            "sources": [],
            "search_query": "",
            "message": "Empty query for web search"
        }

    if not settings.SERPAPI_API_KEY:
        return {
            "success": False,
            "sources": [],
            "search_query": clean_query,
            "message": "SerpApi API key (SERPAPI_API_KEY) is not configured in backend environment."
        }

    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google",
            "q": clean_query,
            "api_key": settings.SERPAPI_API_KEY,
            "num": num_results
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                sources: List[WebSource] = []
                
                # Check knowledge graph or answer box first
                answer_box = data.get("answer_box", {})
                if answer_box and (answer_box.get("snippet") or answer_box.get("answer")):
                    snip = answer_box.get("snippet") or answer_box.get("answer") or ""
                    title = answer_box.get("title", "Google Answer Box")
                    link = answer_box.get("link", f"https://www.google.com/search?q={clean_query}")
                    sources.append(WebSource(
                        title=title,
                        link=link,
                        snippet=snip,
                        source_engine="Google (SerpApi Answer Box)"
                    ))
                
                # Check organic results
                organic = data.get("organic_results", [])
                for item in organic[:num_results]:
                    title = item.get("title", "Web Result")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    if link and snippet:
                        sources.append(WebSource(
                            title=title,
                            link=link,
                            snippet=snippet,
                            source_engine="Google (SerpApi)"
                        ))
                
                return {
                    "success": len(sources) > 0,
                    "sources": sources[:num_results],
                    "search_query": clean_query,
                    "message": None if sources else "No organic search results found."
                }
            else:
                err_msg = f"SerpApi returned status code {resp.status_code}: {resp.text[:200]}"
                print(f"[SerpApi] {err_msg}")
                return {
                    "success": False,
                    "sources": [],
                    "search_query": clean_query,
                    "message": err_msg
                }
    except Exception as e:
        err_msg = f"SerpApi search request failed: {str(e)}"
        print(f"[SerpApi] {err_msg}")
        return {
            "success": False,
            "sources": [],
            "search_query": clean_query,
            "message": err_msg
        }
