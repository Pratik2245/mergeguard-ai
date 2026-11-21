"""
GitLab REST API Integration Service
Fetches Merge Request metadata, changes, and diffs from GitLab to run MergeGuard analysis.
"""

from typing import Dict, Any, Optional
import httpx
from urllib.parse import quote_plus


class GitLabClient:
    def __init__(self, base_url: str = "https://gitlab.com", private_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if private_token:
            self.headers["PRIVATE-TOKEN"] = private_token

    async def fetch_merge_request(self, project_id: str, mr_iid: int) -> Dict[str, Any]:
        """
        Retrieves MR metadata from GitLab REST API:
        GET /api/v4/projects/:id/merge_requests/:merge_request_iid
        """
        encoded_project = quote_plus(project_id)
        url = f"{self.base_url}/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 404:
                raise ValueError(f"GitLab MR !{mr_iid} in project '{project_id}' not found.")
            resp.raise_for_status()
            return resp.json()

    async def fetch_mr_diffs(self, project_id: str, mr_iid: int) -> str:
        """
        Retrieves file diffs for a Merge Request:
        GET /api/v4/projects/:id/merge_requests/:merge_request_iid/diffs
        Converts diff chunks into standard unified git diff format.
        """
        encoded_project = quote_plus(project_id)
        url = f"{self.base_url}/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}/diffs"
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 404:
                raise ValueError(f"Diffs for GitLab MR !{mr_iid} in '{project_id}' not found.")
            resp.raise_for_status()
            diff_entries = resp.json()

        # Reconstruct standard unified git diff format
        diff_text_parts = []
        for entry in diff_entries:
            old_path = entry.get("old_path", "")
            new_path = entry.get("new_path", "")
            diff_content = entry.get("diff", "")
            
            diff_text_parts.append(f"diff --git a/{old_path} b/{new_path}")
            diff_text_parts.append(f"--- a/{old_path}")
            diff_text_parts.append(f"+++ b/{new_path}")
            diff_text_parts.append(diff_content)

        return "\n".join(diff_text_parts)
