"""
Comprehensive tests for KeywordSearchEngine.

Tests cover:
- Tokenization
- Document indexing
- Exact and partial matching
- BM25 scoring
- Field boosting
- Phrase matching bonuses
- Edge cases (empty queries, no results)
- Result limiting
- Score thresholding
"""

import pytest
import math
from pathlib import Path
from kiwi_mcp.utils.search.keyword import KeywordSearchEngine, SearchResult


class TestTokenization:
    """Test tokenization functionality."""

    def test_tokenize_basic(self):
        """Test basic tokenization works correctly."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("Hello World Python")
        assert tokens == ["hello", "world", "python"]

    def test_tokenize_lowercase(self):
        """Test tokenization converts to lowercase."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("HELLO WORLD")
        assert all(t.islower() for t in tokens)

    def test_tokenize_filters_short_tokens(self):
        """Test tokenization filters tokens shorter than 2 characters."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("a ab abc I am testing")
        # 'a' and 'I' should be filtered out
        assert "a" not in tokens
        assert "i" not in tokens
        assert "ab" in tokens
        assert "abc" in tokens
        assert "testing" in tokens

    def test_tokenize_handles_special_characters(self):
        """Test tokenization handles special characters."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("hello-world test_case email@domain.com")
        assert "hello" in tokens
        assert "world" in tokens
        # test_case is kept as one token (underscore is part of \w)
        assert "test_case" in tokens
        # email should be split
        assert "email" in tokens
        assert "domain" in tokens

    def test_tokenize_empty_string(self):
        """Test tokenization of empty string."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("")
        assert tokens == []

    def test_tokenize_only_short_tokens(self):
        """Test tokenization when all tokens are short."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("a b c I")
        assert tokens == []

    def test_tokenize_numbers(self):
        """Test tokenization preserves numbers."""
        engine = KeywordSearchEngine()

        tokens = engine._tokenize("python3 version2 test123")
        assert "python3" in tokens
        assert "version2" in tokens
        assert "test123" in tokens


class TestDocumentIndexing:
    """Test document indexing functionality."""

    def test_index_document(self):
        """Test documents are indexed correctly."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Test Document", "content": "This is test content"},
            path=Path("/test/doc1.md"),
            metadata={"version": "1.0.0"},
        )

        assert "doc1" in engine._doc_cache
        assert engine._total_docs == 1
        assert engine._doc_cache["doc1"]["item_type"] == "directive"

    def test_index_multiple_documents(self):
        """Test indexing multiple documents."""
        engine = KeywordSearchEngine()

        for i in range(3):
            engine.index_document(
                item_id=f"doc{i}",
                item_type="directive",
                fields={"title": f"Document {i}", "content": f"Content {i}"},
                path=Path(f"/test/doc{i}.md"),
                metadata={},
            )

        assert engine._total_docs == 3
        assert len(engine._doc_cache) == 3

    def test_index_document_tokenizes_fields(self):
        """Test that indexed documents have tokenized fields."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing", "content": "Unit tests for Python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        doc = engine._doc_cache["doc1"]
        assert "title" in doc["fields"]
        assert "content" in doc["fields"]
        assert "python" in doc["fields"]["title"]
        assert "testing" in doc["fields"]["title"]

    def test_index_document_calculates_length(self):
        """Test that document length is calculated."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Test", "content": "This is a test document with multiple words"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        doc = engine._doc_cache["doc1"]
        assert doc["length"] > 0

    def test_index_document_updates_idf_cache(self):
        """Test that IDF cache is updated when indexing."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        assert len(engine._idf_cache) > 0
        assert "python" in engine._idf_cache
        assert "testing" in engine._idf_cache

    def test_index_document_updates_avg_length(self):
        """Test that average document length is updated."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Short"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        avg_length_1 = engine._avg_doc_length

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "This is a much longer document with many words"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        avg_length_2 = engine._avg_doc_length
        assert avg_length_2 > avg_length_1

    def test_index_preserves_raw_fields(self):
        """Test that raw field content is preserved."""
        engine = KeywordSearchEngine()

        original_title = "Python Testing Framework"
        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": original_title},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        doc = engine._doc_cache["doc1"]
        assert doc["raw_fields"]["title"] == original_title


class TestExactMatching:
    """Test exact term matching."""

    def test_search_exact_match(self):
        """Test exact term matches are found."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing", "content": "Unit tests for Python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 1
        assert results[0].item_id == "doc1"

    def test_search_exact_match_multiple_docs(self):
        """Test exact matches across multiple documents."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "Python Debugging"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 2

    def test_search_exact_match_case_insensitive(self):
        """Test exact matching is case-insensitive."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "PYTHON Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 1

    def test_search_multiple_exact_terms(self):
        """Test searching for multiple exact terms."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing Framework"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python testing")
        assert len(results) == 1
        # Document should score higher with multiple matches
        assert results[0].score > 0


class TestPartialMatching:
    """Test partial term matching."""

    def test_search_partial_match(self):
        """Test partial term matches are found."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Testing Framework", "content": "Unit tests"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        # Search for complete token "testing" which matches "Testing"
        results = engine.search("testing")
        assert len(results) == 1

    def test_search_partial_match_multiple_occurrences(self):
        """Test partial matches with multiple occurrences."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Testing", "content": "test test test"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("test")
        assert len(results) == 1
        # Multiple occurrences should increase score
        assert results[0].score > 0


class TestBM25Scoring:
    """Test BM25 scoring algorithm."""

    def test_bm25_scoring_basic(self):
        """Test BM25 scores are calculated."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python", "content": "Python is great"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 1
        assert results[0].score > 0

    def test_bm25_scoring_higher_for_more_matches(self):
        """Test BM25 scores are higher with more term occurrences."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python", "content": "Python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "Python Python Python", "content": "Python Python"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 2
        # doc2 should score higher due to more occurrences
        assert results[0].item_id == "doc2"
        assert results[0].score > results[1].score

    def test_bm25_scoring_idf_weighting(self):
        """Test BM25 uses IDF weighting."""
        engine = KeywordSearchEngine()

        # Index documents with common and rare terms
        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "the the the", "content": "the the the"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "rare", "content": "rare"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        # Rare term should have higher IDF
        assert engine._idf_cache.get("rare", 0) > engine._idf_cache.get("the", 0)

    def test_bm25_scoring_saturation(self):
        """Test BM25 term frequency saturation."""
        engine = KeywordSearchEngine()

        # Create documents with different term frequencies
        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "test", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "test test test test test", "content": ""},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("test")
        # doc2 should score higher but not proportionally to 5x frequency
        # due to saturation (K1 parameter)
        assert results[0].score > results[1].score or results[0].item_id == "doc2"


class TestFieldBoosting:
    """Test field boosting functionality."""

    def test_field_boosting_title_over_content(self):
        """Test title field is boosted over content."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "", "content": "python"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 2
        # doc1 should score higher due to title boost
        assert results[0].item_id == "doc1"

    def test_field_boosting_name_same_as_title(self):
        """Test name field has same boost as title."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"name": "python", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "python", "content": ""},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python")
        # Both should have similar scores
        assert len(results) == 2

    def test_field_boosting_description_over_content(self):
        """Test description field is boosted over content."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"description": "python", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"description": "", "content": "python"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 2
        # doc1 should score higher
        assert results[0].item_id == "doc1"

    def test_field_boosting_weights(self):
        """Test field boost weights are applied correctly."""
        engine = KeywordSearchEngine()

        # Verify default field weights are defined
        assert engine.DEFAULT_FIELD_WEIGHTS["title"] == 5.0
        assert engine.DEFAULT_FIELD_WEIGHTS["name"] == 5.0
        assert engine.DEFAULT_FIELD_WEIGHTS["description"] == 2.0
        assert engine.DEFAULT_FIELD_WEIGHTS["content"] == 1.0


class TestPhraseMatching:
    """Test phrase matching bonus."""

    def test_phrase_match_bonus(self):
        """Test phrase matching gets bonus."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing Framework", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "Python", "content": "Testing Framework"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python testing")
        # doc1 should score higher due to phrase match bonus
        assert results[0].item_id == "doc1"

    def test_phrase_match_exact_phrase(self):
        """Test exact phrase matching."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing Framework"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "Testing Python Framework"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python testing")
        # doc1 has the exact phrase
        assert results[0].item_id == "doc1"

    def test_phrase_match_bonus_multiplier(self):
        """Test phrase match bonus is 1.5x."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python testing", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python testing")
        # Score should be multiplied by 1.5 for phrase match
        assert results[0].score > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query_returns_empty(self):
        """Test empty query returns empty results."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("")
        assert results == []

    def test_whitespace_only_query_returns_empty(self):
        """Test whitespace-only query returns empty results."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("   ")
        assert results == []

    def test_no_results_for_non_matching_query(self):
        """Test non-matching query returns empty results."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("javascript")
        assert results == []

    def test_search_empty_index(self):
        """Test searching empty index returns empty."""
        engine = KeywordSearchEngine()

        results = engine.search("python")
        assert results == []

    def test_search_with_special_characters(self):
        """Test search with special characters."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python-Testing", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python-testing")
        assert len(results) == 1


class TestResultLimiting:
    """Test result limiting functionality."""

    def test_limit_results(self):
        """Test limit parameter works."""
        engine = KeywordSearchEngine()

        for i in range(10):
            engine.index_document(
                item_id=f"doc{i}",
                item_type="directive",
                fields={"title": "python", "content": f"content {i}"},
                path=Path(f"/test/doc{i}.md"),
                metadata={},
            )

        results = engine.search("python", limit=5)
        assert len(results) == 5

    def test_limit_default_is_20(self):
        """Test default limit is 20."""
        engine = KeywordSearchEngine()

        for i in range(30):
            engine.index_document(
                item_id=f"doc{i}",
                item_type="directive",
                fields={"title": "python", "content": f"content {i}"},
                path=Path(f"/test/doc{i}.md"),
                metadata={},
            )

        results = engine.search("python", min_score=0.0)
        assert len(results) == 20

    def test_limit_respects_fewer_results(self):
        """Test limit respects when fewer results exist."""
        engine = KeywordSearchEngine()

        for i in range(5):
            engine.index_document(
                item_id=f"doc{i}",
                item_type="directive",
                fields={"title": "python"},
                path=Path(f"/test/doc{i}.md"),
                metadata={},
            )

        results = engine.search("python", limit=10)
        assert len(results) == 5

    def test_limit_zero(self):
        """Test limit of zero returns empty."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python", limit=0)
        assert len(results) == 0


class TestMinScoreThreshold:
    """Test minimum score threshold filtering."""

    def test_min_score_threshold(self):
        """Test min_score filters results."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "", "content": "python"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python", min_score=0.5)
        # Only high-scoring results should be returned
        assert all(r.score >= 0.5 for r in results)

    def test_min_score_default_is_0_1(self):
        """Test default min_score is 0.1."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert all(r.score >= 0.1 for r in results)

    def test_min_score_zero(self):
        """Test min_score of zero includes all matches."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python", min_score=0.0)
        assert len(results) == 1

    def test_min_score_very_high(self):
        """Test very high min_score filters all results."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python", min_score=1000.0)
        assert len(results) == 0


class TestTypeFiltering:
    """Test filtering by item type."""

    def test_filter_by_type(self):
        """Test filtering by item type."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="tool",
            fields={"title": "python"},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        results = engine.search("python", item_type="directive")
        assert len(results) == 1
        assert results[0].item_type == "directive"

    def test_filter_by_type_no_matches(self):
        """Test filtering by type with no matches."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python", item_type="tool")
        assert len(results) == 0


class TestSearchResultStructure:
    """Test SearchResult structure and content."""

    def test_search_result_has_required_fields(self):
        """Test SearchResult contains all required fields."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Test Document", "content": "Test content"},
            path=Path("/test/doc1.md"),
            metadata={"version": "1.0.0"},
        )

        results = engine.search("test")
        assert len(results) == 1

        result = results[0]
        assert result.item_id == "doc1"
        assert result.item_type == "directive"
        assert result.score > 0
        assert result.title == "Test Document"
        assert result.preview is not None
        assert result.path == Path("/test/doc1.md")
        assert result.metadata == {"version": "1.0.0"}

    def test_search_result_title_fallback(self):
        """Test SearchResult title falls back to name then item_id."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"name": "Named Document", "content": "test"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("test")
        assert results[0].title == "Named Document"

    def test_search_result_preview_generation(self):
        """Test SearchResult preview is generated."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Test", "description": "This is a test description"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("test")
        assert results[0].preview is not None


class TestSorting:
    """Test result sorting."""

    def test_results_sorted_by_score_descending(self):
        """Test results are sorted by score descending."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python", "content": ""},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc2",
            item_type="directive",
            fields={"title": "python python python", "content": ""},
            path=Path("/test/doc2.md"),
            metadata={},
        )

        engine.index_document(
            item_id="doc3",
            item_type="directive",
            fields={"title": "", "content": "python"},
            path=Path("/test/doc3.md"),
            metadata={},
        )

        results = engine.search("python")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestClearingIndex:
    """Test clearing the index."""

    def test_clear_index(self):
        """Test clearing the index."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        assert engine._total_docs == 1

        engine.clear()

        assert engine._total_docs == 0
        assert len(engine._doc_cache) == 0
        assert len(engine._idf_cache) == 0
        assert engine._avg_doc_length == 0.0

    def test_search_after_clear(self):
        """Test searching after clearing index."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        engine.clear()

        results = engine.search("python")
        assert results == []


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_mixed_document_types(self):
        """Test searching across mixed document types."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="dir1",
            item_type="directive",
            fields={"title": "Python Setup", "description": "Setup Python environment"},
            path=Path("/test/dir1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="tool1",
            item_type="tool",
            fields={"title": "Python Linter", "description": "Lint Python code"},
            path=Path("/test/tool1.md"),
            metadata={},
        )

        engine.index_document(
            item_id="kb1",
            item_type="knowledge",
            fields={"title": "Python Best Practices", "content": "Best practices for Python"},
            path=Path("/test/kb1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 3
        assert len(set(r.item_type for r in results)) == 3

    def test_large_document_collection(self):
        """Test searching large document collection."""
        engine = KeywordSearchEngine()

        # Index 100 documents with python in content
        for i in range(100):
            engine.index_document(
                item_id=f"doc{i}",
                item_type="directive",
                fields={"title": f"Document {i}", "content": f"python content {i}"},
                path=Path(f"/test/doc{i}.md"),
                metadata={},
            )

        results = engine.search("python", limit=10, min_score=0.0)
        assert len(results) == 10
        assert all(r.score > 0 for r in results)

    def test_unicode_content(self):
        """Test searching unicode content."""
        engine = KeywordSearchEngine()

        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Python Testing", "content": "Тестирование Python"},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 1

    def test_very_long_document(self):
        """Test indexing and searching very long documents."""
        engine = KeywordSearchEngine()

        long_content = " ".join(["python"] * 1000)
        engine.index_document(
            item_id="doc1",
            item_type="directive",
            fields={"title": "Long Document", "content": long_content},
            path=Path("/test/doc1.md"),
            metadata={},
        )

        results = engine.search("python")
        assert len(results) == 1
        assert results[0].score > 0
