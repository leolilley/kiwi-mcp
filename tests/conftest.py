"""
Test configuration and fixtures.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path


# Set up test environment
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = "test-secret-key"


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    
    # Mock table operations
    client.table = MagicMock(return_value=MagicMock())
    client.rpc = MagicMock(return_value=MagicMock())
    
    return client


@pytest.fixture
def mock_directives_search_result():
    """Mock search results for directives."""
    return {
        "data": [
            {
                "id": "1",
                "name": "bootstrap_directive",
                "category": "setup",
                "subcategory": "initialization",
                "description": "Bootstrap a new project with essential configurations",
                "is_official": True,
                "download_count": 150,
                "quality_score": 95.0,
                "tech_stack": ["Python", "CLI"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T00:00:00Z",
            },
            {
                "id": "2",
                "name": "setup_auth",
                "category": "authentication",
                "subcategory": "oauth",
                "description": "Setup OAuth authentication with multiple providers",
                "is_official": False,
                "download_count": 50,
                "quality_score": 80.0,
                "tech_stack": ["Python", "OAuth"],
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-10T00:00:00Z",
            }
        ]
    }


@pytest.fixture
def mock_scripts_search_result():
    """Mock search results for scripts."""
    return {
        "data": [
            {
                "id": "1",
                "name": "google_maps_scraper",
                "category": "scraping",
                "subcategory": "maps",
                "description": "Scrape business locations from Google Maps",
                "is_official": True,
                "download_count": 500,
                "quality_score": 98.0,
                "tech_stack": ["Python", "Selenium"],
                "tags": ["scraping", "google-maps"],
                "success_rate": 0.95,
                "estimated_cost_usd": 0.05,
                "latest_version": "2.1.0",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T00:00:00Z",
            },
            {
                "id": "2",
                "name": "email_validator",
                "category": "validation",
                "subcategory": "email",
                "description": "Validate email addresses and check deliverability",
                "is_official": False,
                "download_count": 200,
                "quality_score": 85.0,
                "tech_stack": ["Python", "Email"],
                "tags": ["email", "validation"],
                "success_rate": 0.90,
                "estimated_cost_usd": 0.01,
                "latest_version": "1.5.0",
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-10T00:00:00Z",
            }
        ]
    }


@pytest.fixture
def mock_knowledge_search_result():
    """Mock search results for knowledge entries."""
    return {
        "data": [
            {
                "zettel_id": "001-email-deliverability",
                "title": "Email Deliverability Best Practices",
                "entry_type": "pattern",
                "category": "email-infrastructure",
                "tags": ["email", "smtp", "deliverability"],
                "snippet": "Email deliverability refers to the ability of a transactional email to reach its intended email inbox.",
            },
            {
                "zettel_id": "002-jwt-auth",
                "title": "JWT Authentication in Python",
                "entry_type": "learning",
                "category": "authentication",
                "tags": ["jwt", "python", "auth"],
                "snippet": "JWT tokens are self-contained and can be used for stateless authentication.",
            }
        ]
    }


@pytest.fixture
def directive_registry(monkeypatch):
    """Create a DirectiveRegistry with mocked Supabase client."""
    from kiwi_mcp.api.directive_registry import DirectiveRegistry
    
    registry = DirectiveRegistry()
    # Mock the client to avoid actual connection attempts
    registry.client = MagicMock()
    return registry


@pytest.fixture
def script_registry(monkeypatch):
    """Create a ScriptRegistry with mocked Supabase client."""
    from kiwi_mcp.api.script_registry import ScriptRegistry
    
    registry = ScriptRegistry()
    # Mock the client to avoid actual connection attempts
    registry.client = MagicMock()
    return registry


@pytest.fixture
def knowledge_registry(monkeypatch):
    """Create a KnowledgeRegistry with mocked Supabase client."""
    from kiwi_mcp.api.knowledge_registry import KnowledgeRegistry
    
    registry = KnowledgeRegistry()
    # Mock the client to avoid actual connection attempts
    registry.client = MagicMock()
    return registry


@pytest.fixture
def mock_filesystem(tmp_path):
    """Create a mock filesystem for testing."""
    return {
        "project_root": tmp_path,
        "directives_dir": tmp_path / ".ai" / "directives",
        "scripts_dir": tmp_path / ".ai" / "scripts",
        "knowledge_dir": tmp_path / ".ai" / "knowledge",
    }
