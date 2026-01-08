import requests
import json
from datetime import datetime, timedelta

# --- GitHub Integration ---

GITHUB_API_URL = "https://api.github.com"

def get_github_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_github_repos(token):
    """
    Fetches the list of repositories for the authenticated user.
    """
    try:
        url = f"{GITHUB_API_URL}/user/repos?sort=updated&per_page=10"
        response = requests.get(url, headers=get_github_headers(token))
        
        if response.status_code == 200:
            repos = response.json()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "html_url": r["html_url"],
                    "description": r.get("description", ""),
                    "stars": r["stargazers_count"]
                }
                for r in repos
            ]
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# --- OneNote Integration (Microsoft Graph) ---

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

def get_graph_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def fetch_onenote_pages(token):
    """
    Fetches recent pages from the user's OneNote.
    """
    try:
        # Get pages from all sections, ordered by last modified
        url = f"{GRAPH_API_URL}/me/onenote/pages?$top=10&$orderby=lastModifiedDateTime desc&$select=id,title,links"
        response = requests.get(url, headers=get_graph_headers(token))
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get("value", [])
            return [
                {
                    "id": p["id"],
                    "title": p["title"],
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
