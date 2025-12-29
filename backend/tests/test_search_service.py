"""Tests for search service

Unit tests for SearchService class with mocked MeiliSearch client,
testing indexing, searching, deletion, and graceful degradation.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestSearchServiceInitialization:
    """Tests for SearchService initialization and graceful degradation"""

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_init_without_meilisearch(self, mock_settings, mock_client_class):
        """Test graceful degradation when MeiliSearch is unavailable"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        # Simulate connection failure
        mock_client_class.side_effect = Exception("Connection refused")

        from app.services.search import SearchService

        service = SearchService()

        # Should not crash, but index should be None
        assert service.index is None

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_init_with_meilisearch_success(self, mock_settings, mock_client_class):
        """Test successful initialization with MeiliSearch"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()

        assert service.client is not None
        assert service.index is not None


class TestSearchServiceIndexCommand:
    """Tests for SearchService.index_command()"""

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_index_command_success(self, mock_settings, mock_client_class):
        """Test successful command indexing"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_task = MagicMock(task_uid=123)
        mock_index.add_documents.return_value = mock_task
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()

        # Create a mock command
        mock_command = MagicMock()
        mock_command.id = uuid4()
        mock_command.command = "ls -la"
        mock_command.hostname = "test-host"
        mock_command.username = "testuser"
        mock_command.exit_code = 0
        mock_command.timestamp = None
        mock_command.user_id = uuid4()

        result = service.index_command(mock_command)

        assert result is not None
        mock_index.add_documents.assert_called_once()

    def test_index_command_no_index_returns_none(self):
        """Test that index_command returns None when no index available"""
        from app.services.search import SearchService

        with patch.object(SearchService, "_init_client"):
            service = SearchService()
            service.index = None

            mock_command = MagicMock()
            result = service.index_command(mock_command)

            assert result is None


class TestSearchServiceSearch:
    """Tests for SearchService.search()"""

    def test_search_returns_empty_when_no_index(self):
        """Test that search returns empty results when no index available"""
        from app.services.search import SearchService

        with patch.object(SearchService, "_init_client"):
            service = SearchService()
            service.index = None

            result = service.search("query", str(uuid4()))

            assert result == {"hits": [], "total": 0}

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_search_with_filters(self, mock_settings, mock_client_class):
        """Test search with additional filters"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_index.search.return_value = {
            "hits": [{"command": "ls", "hostname": "host1"}],
            "totalHits": 1,
        }
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()
        user_id = str(uuid4())

        result = service.search(
            "ls",
            user_id,
            filters={"hostname": "host1", "username": "testuser"},
        )

        assert result["total"] == 1
        assert len(result["hits"]) == 1

        # Verify filter string was constructed correctly
        # search() is called with (query, search_params) where search_params is a dict
        call_args = mock_index.search.call_args
        search_params = call_args[0][1]  # Second positional argument
        filter_string = search_params["filter"]
        assert f'user_id = "{user_id}"' in filter_string
        assert 'hostname = "host1"' in filter_string
        assert 'username = "testuser"' in filter_string

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_search_with_user_id_filter(self, mock_settings, mock_client_class):
        """Test that user_id filter is always applied (multi-tenancy)"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_index.search.return_value = {"hits": [], "totalHits": 0}
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()
        user_id = str(uuid4())

        service.search("query", user_id)

        # Verify user_id filter was applied
        call_args = mock_index.search.call_args
        search_params = call_args[0][1]  # Second positional argument
        filter_string = search_params["filter"]
        assert f'user_id = "{user_id}"' in filter_string


class TestSearchServiceDelete:
    """Tests for SearchService.delete_command()"""

    def test_delete_command_no_index_returns_false(self):
        """Test that delete returns False when no index available"""
        from app.services.search import SearchService

        with patch.object(SearchService, "_init_client"):
            service = SearchService()
            service.index = None

            result = service.delete_command(str(uuid4()))

            assert result is False

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_delete_command_success(self, mock_settings, mock_client_class):
        """Test successful command deletion"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()
        command_id = str(uuid4())

        result = service.delete_command(command_id)

        assert result is True
        mock_index.delete_document.assert_called_once_with(command_id)

    @patch("app.services.search.meilisearch.Client")
    @patch("app.services.search.settings")
    def test_delete_command_failure_returns_false(
        self, mock_settings, mock_client_class
    ):
        """Test that delete returns False on exception"""
        mock_settings.meilisearch_url = "http://localhost:7700"
        mock_settings.meilisearch_master_key = "test-key"

        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_index.delete_document.side_effect = Exception("Delete failed")
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)
        mock_client_class.return_value = mock_client

        from app.services.search import SearchService

        service = SearchService()

        result = service.delete_command(str(uuid4()))

        assert result is False
