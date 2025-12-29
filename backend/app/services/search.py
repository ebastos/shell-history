"""Search service using Meilisearch"""

from typing import Any

import meilisearch
from app.config import settings
from app.models import Command
from meilisearch.index import Index


class SearchService:
    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        self.url: str = url or settings.meilisearch_url
        self.api_key: str = api_key or settings.meilisearch_master_key
        self.client: meilisearch.Client | None = None
        self.index: Index | None = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Meilisearch client and index"""
        try:
            self.client = meilisearch.Client(
                self.url, self.api_key if self.api_key else None
            )
            self._ensure_index()
        except Exception:
            # Meilisearch not available, will use database fallback
            pass

    def _ensure_index(self) -> None:
        """Ensure the commands index exists and is configured"""
        if not self.client:
            return

        try:
            # Create index if it doesn't exist
            try:
                task = self.client.create_index("commands", {"primaryKey": "id"})
                self.client.wait_for_task(task.task_uid)
            except meilisearch.errors.MeilisearchApiError:
                # Index already exists
                pass

            self.index = self.client.index("commands")

            # Configure searchable attributes
            self.index.update_searchable_attributes(["command", "hostname", "username"])

            # Configure filterable attributes
            self.index.update_filterable_attributes(
                ["hostname", "username", "exit_code", "timestamp", "user_id"]
            )

            # Configure sortable attributes
            self.index.update_sortable_attributes(["timestamp"])
        except Exception:
            # Index configuration failed, continue without search
            pass

    def index_command(self, command: Command) -> Any:
        """Index a command in Meilisearch.

        Returns TaskInfo from meilisearch or None if indexing fails.
        """
        if not self.index:
            return None

        try:
            document = {
                "id": str(command.id),
                "command": command.command,
                "hostname": command.hostname,
                "username": command.username,
                "exit_code": command.exit_code,
                "timestamp": command.timestamp.isoformat()
                if command.timestamp
                else None,
                "user_id": str(command.user_id) if command.user_id else None,
            }

            task = self.index.add_documents([document])
            return task
        except Exception:
            return None

    def search(
        self,
        query: str,
        user_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search for commands filtered by user_id.

        Args:
            query: Search query string
            user_id: User ID to filter by (required for multi-tenancy)
            filters: Additional filters (hostname, username, exit_code)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            Dictionary containing 'hits', 'total', and other metadata.
        """
        if not self.index:
            return {"hits": [], "total": 0}

        try:
            # Using dict[str, Any] to allow both int and str values
            search_params: dict[str, Any] = {"limit": limit, "offset": offset}

            # Build filter array - safer than string concatenation
            # Always include user_id filter first
            filter_array: list[str] = [f'user_id = "{user_id}"']

            if filters:
                # Escape and validate hostname filter
                if filters.get("hostname"):
                    hostname = str(filters["hostname"]).strip()
                    # Remove any quotes or special characters that could break filter syntax
                    hostname_escaped = hostname.replace('"', "").replace("'", "")
                    if hostname_escaped:
                        filter_array.append(f'hostname = "{hostname_escaped}"')

                # Escape and validate username filter
                if filters.get("username"):
                    username = str(filters["username"]).strip()
                    username_escaped = username.replace('"', "").replace("'", "")
                    if username_escaped:
                        filter_array.append(f'username = "{username_escaped}"')

                # Validate exit_code is an integer
                if filters.get("exit_code") is not None:
                    try:
                        exit_code = int(filters["exit_code"])
                        filter_array.append(f"exit_code = {exit_code}")
                    except (ValueError, TypeError):
                        pass  # Ignore invalid exit_code

            if filter_array:
                # Use array syntax for filters (safer than string concatenation)
                search_params["filter"] = filter_array

            results = self.index.search(query, search_params)
            # Ensure we return a consistent format
            return {
                "hits": results.get("hits", []),
                "total": results.get("totalHits")
                or results.get("nbHits")
                or len(results.get("hits", [])),
                "query": query,
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            print(f"Meilisearch search error: {e}")
            return {"hits": [], "total": 0}

    def delete_command(self, command_id: str) -> bool:
        """Delete a command from the index"""
        if not self.index:
            return False

        try:
            self.index.delete_document(command_id)
            return True
        except Exception:
            return False


# Global search service instance
search_service = SearchService()
