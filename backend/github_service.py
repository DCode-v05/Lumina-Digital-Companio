import requests
from datetime import datetime, timedelta

# --- GitHub Integration ---

GITHUB_API_URL = "https://api.github.com"

def get_github_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_github_repos(token, per_page=100):
    """
    Fetches all repositories for the authenticated user.
    """
    try:
        # Add type=owner to fetch only owned repos (not org repos or repos with access)
        url = f"{GITHUB_API_URL}/user/repos?type=owner&sort=updated&per_page={per_page}"
        response = requests.get(url, headers=get_github_headers(token))
        
        if response.status_code == 200:
            repos = response.json()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "html_url": r["html_url"],
                    "description": r.get("description", ""),
                    "stars": r["stargazers_count"],
                    "private": r["private"],
                    "language": r.get("language", "")
                }
                for r in repos
            ]
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_github_repo_count(token):
    """
    Gets total count of user repositories.
    """
    try:
        repos = fetch_github_repos(token, per_page=100)
        if isinstance(repos, dict) and "error" in repos:
            return repos
        return {"count": len(repos)}
    except Exception as e:
        return {"error": str(e)}

def create_github_repo(token, name, private=False, description=""):
    """
    Creates a new GitHub repository.
    """
    try:
        url = f"{GITHUB_API_URL}/user/repos"
        payload = {
            "name": name,
            "private": private,
            "description": description
        }
        response = requests.post(url, json=payload, headers=get_github_headers(token))
        
        if response.status_code == 201:
            r = response.json()
            return {
                "id": r["id"],
                "name": r["name"],
                "full_name": r["full_name"],
                "html_url": r["html_url"],
                "description": r.get("description", ""),
                "private": r["private"]
            }
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        elif response.status_code == 422:
            return {"error": "Repository already exists or invalid name."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_github_repo(token, owner, repo):
    """
    Gets details of a specific repository.
    """
    try:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        response = requests.get(url, headers=get_github_headers(token))
        
        if response.status_code == 200:
            r = response.json()
            return {
                "id": r["id"],
                "name": r["name"],
                "full_name": r["full_name"],
                "html_url": r["html_url"],
                "description": r.get("description", ""),
                "stars": r["stargazers_count"],
                "forks": r["forks_count"],
                "language": r.get("language", ""),
                "private": r["private"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            }
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        elif response.status_code == 404:
            return {"error": "Repository not found."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def update_github_repo(token, owner, repo, new_name=None, description=None):
    """
    Updates a GitHub repository.
    """
    try:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        payload = {}
        if new_name:
            payload["name"] = new_name
        if description is not None:
            payload["description"] = description
            
        response = requests.patch(url, json=payload, headers=get_github_headers(token))
        
        if response.status_code == 200:
            r = response.json()
            return {
                "id": r["id"],
                "name": r["name"],
                "full_name": r["full_name"],
                "html_url": r["html_url"],
                "description": r.get("description", "")
            }
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        elif response.status_code == 404:
            return {"error": "Repository not found."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def delete_github_repo(token, owner, repo):
    """
    Deletes a GitHub repository.
    """
    try:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        response = requests.delete(url, headers=get_github_headers(token))
        
        if response.status_code == 204:
            return {"message": "Repository deleted successfully"}
        elif response.status_code == 401:
            return {"error": "Unauthorized. Token invalid."}
        elif response.status_code == 404:
            return {"error": "Repository not found."}
        else:
            return {"error": f"GitHub API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
