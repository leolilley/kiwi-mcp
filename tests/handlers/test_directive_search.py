"""
Tests for directive search functionality.

Tests the DirectiveHandler.search() method with various scenarios:
- Finding directives by name
- Finding directives by description
- Correct result format
- Respecting limit parameter
- Score ranking
- Handling missing metadata
"""

import pytest
from pathlib import Path
from typing import Dict, Any
import asyncio

from kiwi_mcp.handlers.directive import DirectiveHandler


# Sample directive templates
DIRECTIVE_TEMPLATE = """# {name}

```xml
<directive name="{name}" version="1.0.0">
  <metadata>
    <description>{description}</description>
    <category>{category}</category>
    <author>test</author>
    <model tier="fast">Test directive</model>
    <permissions>
      <read resource="filesystem" path="**/*" />
    </permissions>
  </metadata>
  <context>
    <tech_stack>any</tech_stack>
  </context>
  <inputs>
    <input name="query" type="string" required="true">Search query</input>
  </inputs>
  <process>
    <step name="search">
      <description>Perform search</description>
      <action>Search for items</action>
    </step>
  </process>
  <outputs>
    <success>Search completed</success>
  </outputs>
</directive>
```
"""

MINIMAL_DIRECTIVE_TEMPLATE = """# {name}

```xml
<directive name="{name}" version="1.0.0">
  <metadata>
    <description>{description}</description>
    <category>{category}</category>
    <permissions>
      <read resource="filesystem" path="**/*" />
    </permissions>
  </metadata>
  <inputs>
  </inputs>
  <process>
    <step name="test">
      <description>Test step</description>
      <action>Test action</action>
    </step>
  </process>
</directive>
```
"""


@pytest.fixture
def project_path(tmp_path):
    """Create a temporary project directory with .ai structure."""
    ai_dir = tmp_path / ".ai"
    directives_dir = ai_dir / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def handler(project_path):
    """Create a DirectiveHandler instance."""
    return DirectiveHandler(str(project_path))


@pytest.fixture
def test_directives(project_path):
    """Create test directive files."""
    directives_dir = project_path / ".ai" / "directives"

    # Create category subdirectories
    (directives_dir / "search").mkdir(parents=True, exist_ok=True)
    (directives_dir / "data").mkdir(parents=True, exist_ok=True)
    (directives_dir / "utils").mkdir(parents=True, exist_ok=True)

    directives = {
        "search_directives": {
            "path": directives_dir / "search" / "search_directives.md",
            "name": "search_directives",
            "description": "Search for directives by keyword and filter",
            "category": "search",
        },
        "search_knowledge": {
            "path": directives_dir / "search" / "search_knowledge.md",
            "name": "search_knowledge",
            "description": "Search knowledge base for information",
            "category": "search",
        },
        "load_directive": {
            "path": directives_dir / "utils" / "load_directive.md",
            "name": "load_directive",
            "description": "Load a directive from project or user space",
            "category": "utils",
        },
        "create_data_pipeline": {
            "path": directives_dir / "data" / "create_data_pipeline.md",
            "name": "create_data_pipeline",
            "description": "Create a data processing pipeline with validation",
            "category": "data",
        },
        "validate_schema": {
            "path": directives_dir / "data" / "validate_schema.md",
            "name": "validate_schema",
            "description": "Validate data against JSON schema",
            "category": "data",
        },
    }

    # Create directive files
    for key, info in directives.items():
        content = DIRECTIVE_TEMPLATE.format(
            name=info["name"],
            description=info["description"],
            category=info["category"],
        )
        info["path"].write_text(content)

    return directives


@pytest.fixture
def minimal_directives(project_path):
    """Create minimal directive files (missing some metadata)."""
    directives_dir = project_path / ".ai" / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)

    # Create a directive with minimal metadata
    minimal_path = directives_dir / "minimal_directive.md"
    content = MINIMAL_DIRECTIVE_TEMPLATE.format(
        name="minimal_directive",
        description="A minimal directive",
        category="test",
    )
    minimal_path.write_text(content)

    return {"minimal_directive": minimal_path}


class TestDirectiveSearchByName:
    """Test searching directives by name."""

    @pytest.mark.asyncio
    async def test_search_finds_directive_by_name(self, handler, test_directives):
        """Test that search finds directives by exact name match."""
        result = await handler.search("search_directives")

        assert result["query"] == "search_directives"
        assert result["total"] > 0
        assert len(result["results"]) > 0

        # Check that the matching directive is in results
        names = [r["name"] for r in result["results"]]
        assert "search_directives" in names

    @pytest.mark.asyncio
    async def test_search_finds_multiple_by_partial_name(self, handler, test_directives):
        """Test that search finds multiple directives with partial name match."""
        result = await handler.search("search")

        assert result["total"] >= 2
        names = [r["name"] for r in result["results"]]
        assert "search_directives" in names
        assert "search_knowledge" in names

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, handler, test_directives):
        """Test that search is case-insensitive."""
        result_lower = await handler.search("search_directives")
        result_upper = await handler.search("SEARCH_DIRECTIVES")
        result_mixed = await handler.search("Search_Directives")

        # All should find the same directive
        lower_names = [r["name"] for r in result_lower["results"]]
        upper_names = [r["name"] for r in result_upper["results"]]
        mixed_names = [r["name"] for r in result_mixed["results"]]

        assert "search_directives" in lower_names
        assert "search_directives" in upper_names
        assert "search_directives" in mixed_names


class TestDirectiveSearchByDescription:
    """Test searching directives by description."""

    @pytest.mark.asyncio
    async def test_search_finds_directive_by_description(self, handler, test_directives):
        """Test that search finds directives by description keywords."""
        result = await handler.search("keyword filter")

        assert result["total"] > 0
        names = [r["name"] for r in result["results"]]
        assert "search_directives" in names

    @pytest.mark.asyncio
    async def test_search_finds_by_domain_keyword(self, handler, test_directives):
        """Test that search finds directives by domain-specific keywords."""
        result = await handler.search("data processing pipeline")

        assert result["total"] > 0
        names = [r["name"] for r in result["results"]]
        assert "create_data_pipeline" in names

    @pytest.mark.asyncio
    async def test_search_finds_by_single_keyword(self, handler, test_directives):
        """Test that search finds directives by single keyword."""
        # Search for a keyword that's in our test directives
        result = await handler.search("data")

        assert result["total"] > 0
        names = [r["name"] for r in result["results"]]
        # Should find at least one directive with "data" in name or description
        assert any("data" in name.lower() for name in names)


class TestDirectiveSearchFormat:
    """Test that search returns correct result format."""

    @pytest.mark.asyncio
    async def test_search_returns_correct_format(self, handler, test_directives):
        """Test that search results have correct structure."""
        result = await handler.search("search")

        # Check top-level structure
        assert "query" in result
        assert "source" in result
        assert "results" in result
        assert "total" in result

        # Check result item structure
        for item in result["results"]:
            assert "name" in item
            assert "description" in item
            assert "version" in item
            assert "score" in item
            assert "source" in item
            assert "path" in item

            # Validate types
            assert isinstance(item["name"], str)
            assert isinstance(item["description"], str)
            assert isinstance(item["version"], str)
            assert isinstance(item["score"], (int, float))
            assert isinstance(item["source"], str)
            assert isinstance(item["path"], str)

    @pytest.mark.asyncio
    async def test_search_result_source_is_project(self, handler, test_directives):
        """Test that results correctly identify source as 'project' or 'user'."""
        result = await handler.search("search")

        # Results can be from project or user space
        for item in result["results"]:
            assert item["source"] in ("project", "user")

    @pytest.mark.asyncio
    async def test_search_result_path_is_valid(self, handler, test_directives):
        """Test that result paths are valid file paths."""
        result = await handler.search("search")

        for item in result["results"]:
            path = Path(item["path"])
            assert path.exists()
            assert path.is_file()
            assert path.suffix == ".md"


class TestDirectiveSearchLimit:
    """Test that search respects limit parameter."""

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, handler, test_directives):
        """Test that search respects the limit parameter."""
        result_limit_2 = await handler.search("directive", limit=2)
        result_limit_5 = await handler.search("directive", limit=5)
        result_no_limit = await handler.search("directive", limit=100)

        assert len(result_limit_2["results"]) <= 2
        assert len(result_limit_5["results"]) <= 5
        assert len(result_no_limit["results"]) <= 100

    @pytest.mark.asyncio
    async def test_search_limit_zero(self, handler, test_directives):
        """Test that limit=0 returns empty results."""
        result = await handler.search("search", limit=0)

        assert len(result["results"]) == 0
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_limit_one(self, handler, test_directives):
        """Test that limit=1 returns at most one result."""
        result = await handler.search("directive", limit=1)

        assert len(result["results"]) <= 1

    @pytest.mark.asyncio
    async def test_search_default_limit(self, handler, test_directives):
        """Test that default limit is applied."""
        result = await handler.search("directive")

        # Default limit is 10
        assert len(result["results"]) <= 10


class TestDirectiveSearchScoring:
    """Test that search scores are ranked correctly."""

    @pytest.mark.asyncio
    async def test_search_scores_are_ranked(self, handler, test_directives):
        """Test that results are ranked by score (highest first)."""
        result = await handler.search("search")

        if len(result["results"]) > 1:
            scores = [r["score"] for r in result["results"]]
            # Scores should be in descending order
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_exact_match_scores_higher(self, handler, test_directives):
        """Test that exact name matches score higher than partial matches."""
        result = await handler.search("search_directives")

        if len(result["results"]) > 0:
            # First result should be the exact match
            first_result = result["results"][0]
            assert first_result["name"] == "search_directives"

            # Its score should be highest
            first_score = first_result["score"]
            for item in result["results"][1:]:
                assert item["score"] <= first_score

    @pytest.mark.asyncio
    async def test_search_all_query_terms_scores_higher(self, handler, test_directives):
        """Test that results matching all query terms score higher."""
        result = await handler.search("search directives")

        if len(result["results"]) > 1:
            # Results should be sorted by score
            scores = [r["score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_score_is_numeric(self, handler, test_directives):
        """Test that all scores are numeric values."""
        result = await handler.search("search")

        for item in result["results"]:
            assert isinstance(item["score"], (int, float))
            assert item["score"] >= 0


class TestDirectiveSearchMissingMetadata:
    """Test handling of directives with missing metadata."""

    @pytest.mark.asyncio
    async def test_search_handles_missing_metadata(self, handler, minimal_directives):
        """Test that search handles directives with minimal metadata."""
        result = await handler.search("minimal")

        # Should not crash and should find the directive
        assert isinstance(result, dict)
        assert "results" in result

        # The minimal directive should be found
        names = [r["name"] for r in result["results"]]
        assert "minimal_directive" in names

    @pytest.mark.asyncio
    async def test_search_result_has_defaults_for_missing_fields(self, handler, minimal_directives):
        """Test that missing fields have sensible defaults."""
        result = await handler.search("minimal")

        for item in result["results"]:
            # All required fields should be present
            assert "name" in item
            assert "description" in item
            assert "version" in item
            assert "score" in item
            assert "source" in item
            assert "path" in item

            # Fields should not be None
            assert item["name"] is not None
            assert item["version"] is not None


class TestDirectiveSearchEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_search_empty_query(self, handler, test_directives):
        """Test search with empty query string."""
        result = await handler.search("")

        # Empty query should return no results
        assert result["total"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_no_matches(self, handler, test_directives):
        """Test search with query that matches nothing."""
        result = await handler.search("nonexistent_xyz_abc_123")

        assert result["total"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_special_characters(self, handler, test_directives):
        """Test search with special characters in query."""
        result = await handler.search("search_directives")

        # Should handle underscores
        assert result["total"] > 0

    @pytest.mark.asyncio
    async def test_search_whitespace_handling(self, handler, test_directives):
        """Test search with extra whitespace."""
        result1 = await handler.search("search directives")
        result2 = await handler.search("  search   directives  ")

        # Both should find results
        assert result1["total"] > 0
        assert result2["total"] > 0

    @pytest.mark.asyncio
    async def test_search_returns_dict(self, handler, test_directives):
        """Test that search always returns a dict."""
        result = await handler.search("search")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_search_with_source_parameter(self, handler, test_directives):
        """Test search with source parameter."""
        result = await handler.search("search", source="local")

        assert result["source"] == "local"
        assert isinstance(result["results"], list)


class TestDirectiveSearchSorting:
    """Test search result sorting."""

    @pytest.mark.asyncio
    async def test_search_default_sort_by_score(self, handler, test_directives):
        """Test that default sorting is by score."""
        result = await handler.search("search")

        if len(result["results"]) > 1:
            scores = [r["score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_sort_by_name(self, handler, test_directives):
        """Test sorting by name."""
        result = await handler.search("directive", sort_by="name")

        if len(result["results"]) > 1:
            names = [r["name"] for r in result["results"]]
            assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_search_sort_by_date(self, handler, test_directives):
        """Test sorting by date."""
        result = await handler.search("directive", sort_by="date")

        # Should not crash
        assert isinstance(result["results"], list)


class TestDirectiveSearchIntegration:
    """Integration tests for directive search."""

    @pytest.mark.asyncio
    async def test_search_multiple_queries(self, handler, test_directives):
        """Test multiple sequential searches."""
        result1 = await handler.search("search")
        result2 = await handler.search("data")
        result3 = await handler.search("validate")

        # All should return valid results
        assert result1["total"] >= 2
        assert result2["total"] >= 2
        assert result3["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_consistency(self, handler, test_directives):
        """Test that repeated searches return consistent results."""
        result1 = await handler.search("search")
        result2 = await handler.search("search")

        # Same query should return same results
        names1 = sorted([r["name"] for r in result1["results"]])
        names2 = sorted([r["name"] for r in result2["results"]])
        assert names1 == names2

    @pytest.mark.asyncio
    async def test_search_with_limit_and_sort(self, handler, test_directives):
        """Test search with both limit and sort parameters."""
        result = await handler.search("directive", limit=3, sort_by="name")

        assert len(result["results"]) <= 3
        if len(result["results"]) > 1:
            names = [r["name"] for r in result["results"]]
            assert names == sorted(names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
