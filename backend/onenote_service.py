import requests
from datetime import datetime, timedelta

# --- OneNote Integration (Microsoft Graph) - Read-Only ---

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def get_graph_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def fetch_onenote_pages(token, top=100):
    """
    Fetches recent pages from the user's OneNote.
    """
    try:
        url = f"{GRAPH_API_URL}/me/onenote/pages?$top={top}&$orderby=lastModifiedDateTime desc&$select=id,title,createdDateTime,lastModifiedDateTime,links"
        response = requests.get(url, headers=get_graph_headers(token))
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get("value", [])
            return [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "created_at": p.get("createdDateTime", ""),
                    "modified_at": p.get("lastModifiedDateTime", ""),
                    "links": p.get("links", {})
                }
                for p in pages
            ]
        elif response.status_code == 401:
             return {"error": "Unauthorized. Token invalid."}
        else:
             return {"error": f"Graph API Error: {response.status_code}"}

    except Exception as e:
        return {"error": str(e)}

def get_onenote_page_count(token):
    """
    Gets total count of OneNote pages.
    """
    try:
        pages = fetch_onenote_pages(token, top=1000)
        if isinstance(pages, dict) and "error" in pages:
            return pages
        return {"count": len(pages)}
    except Exception as e:
        return {"error": str(e)}

def get_onenote_sections(token):
    """
    Gets all OneNote sections.
    """
    try:
        url = f"{GRAPH_API_URL}/me/onenote/sections?$select=id,displayName"
        response = requests.get(url, headers=get_graph_headers(token))
        
        if response.status_code == 200:
            data = response.json()
            sections = data.get("value", [])
            return [
                {
                    "id": s["id"],
                    "name": s["displayName"]
                }
                for s in sections
            ]
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        else:
            return {"error": f"Graph API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_onenote_page(token, page_id):
    """
    Gets details of a specific OneNote page.
    """
    try:
        url = f"{GRAPH_API_URL}/me/onenote/pages/{page_id}?$select=id,title,createdDateTime,lastModifiedDateTime,links"
        response = requests.get(url, headers=get_graph_headers(token))
        
        if response.status_code == 200:
            p = response.json()
            return {
                "id": p["id"],
                "title": p["title"],
                "created_at": p.get("createdDateTime", ""),
                "modified_at": p.get("lastModifiedDateTime", ""),
                "links": p.get("links", {})
            }
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        elif response.status_code == 404:
            return {"error": "Page not found."}
        else:
            return {"error": f"Graph API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
