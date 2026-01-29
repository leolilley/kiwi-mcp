"""
Scoring utilities for search ranking and relevance calculation.

This module provides various scoring functions used in search ranking:
- BM25: Probabilistic ranking function
- TF-IDF: Term frequency-inverse document frequency
- Score normalization: Convert scores to 0-1 range
- Field score combination: Weighted combination of field scores
"""

from typing import Dict

# Default field weights for combining scores across different fields
DEFAULT_FIELD_WEIGHTS = {
    "title": 3.0,
    "name": 3.0,
    "description": 2.0,
    "content": 1.0,
}

# BM25 parameters
BM25_K1 = 1.5  # Controls term frequency saturation point
BM25_B = 0.75  # Controls how much effect document length has on relevance


def bm25_score(
    tf: float,
    idf: float,
    doc_length: int,
    avg_doc_length: float,
    k1: float = BM25_K1,
    b: float = BM25_B,
) -> float:
    """
    Calculate BM25 score for a term in a document.

    BM25 (Best Matching 25) is a probabilistic ranking function that considers:
    - Term frequency (tf): How often the term appears in the document
    - Inverse document frequency (idf): How rare the term is across documents
    - Document length: Normalized by average document length
    - Parameters k1 and b: Control saturation and length normalization

    Args:
        tf: Term frequency (count of term in document)
        idf: Inverse document frequency (log of document ratio)
        doc_length: Length of the document (word count)
        avg_doc_length: Average document length in corpus
        k1: Term frequency saturation parameter (default: 1.5)
        b: Length normalization parameter (default: 0.75)

    Returns:
        BM25 score as a float

    Example:
        >>> score = bm25_score(tf=5, idf=2.5, doc_length=100, avg_doc_length=150)
        >>> isinstance(score, float)
        True
    """
    if avg_doc_length == 0:
        return 0.0

    # Length normalization factor
    length_norm = 1 - b + b * (doc_length / avg_doc_length)

    # BM25 formula: IDF * (tf * (k1 + 1)) / (tf + k1 * length_norm)
    numerator = tf * (k1 + 1)
    denominator = tf + k1 * length_norm

    return idf * (numerator / denominator)


def tf_idf_score(tf: float, idf: float) -> float:
    """
    Calculate TF-IDF score for a term.

    TF-IDF (Term Frequency-Inverse Document Frequency) is a simple scoring
    function that combines:
    - Term frequency (tf): How often the term appears in the document
    - Inverse document frequency (idf): How rare the term is across documents

    Args:
        tf: Term frequency (count of term in document)
        idf: Inverse document frequency (log of document ratio)

    Returns:
        TF-IDF score as a float

    Example:
        >>> score = tf_idf_score(tf=5, idf=2.5)
        >>> score == 12.5
        True
    """
    return tf * idf


def normalize_score(score: float, min_score: float, max_score: float) -> float:
    """
    Normalize a score to the 0-1 range.

    Converts a score from an arbitrary range [min_score, max_score] to [0, 1].
    Handles edge cases where min_score equals max_score.

    Args:
        score: The score to normalize
        min_score: Minimum possible score in the original range
        max_score: Maximum possible score in the original range

    Returns:
        Normalized score in the range [0, 1]

    Example:
        >>> normalize_score(score=50, min_score=0, max_score=100)
        0.5
        >>> normalize_score(score=100, min_score=0, max_score=100)
        1.0
        >>> normalize_score(score=0, min_score=0, max_score=100)
        0.0
    """
    if max_score == min_score:
        # If all scores are the same, return 0.5 (middle of range)
        return 0.5

    # Linear normalization: (score - min) / (max - min)
    normalized = (score - min_score) / (max_score - min_score)

    # Clamp to [0, 1] range to handle floating point edge cases
    return max(0.0, min(1.0, normalized))


def combine_field_scores(
    field_scores: Dict[str, float],
    weights: Dict[str, float] | None = None,
) -> float:
    """
    Combine scores from multiple fields using weighted average.

    Calculates a weighted average of scores from different fields (e.g., title,
    description, content). Fields not in field_scores are ignored. Fields not
    in weights use a default weight of 1.0.

    Args:
        field_scores: Dictionary mapping field names to their scores
        weights: Dictionary mapping field names to their weights.
                If None, uses DEFAULT_FIELD_WEIGHTS.

    Returns:
        Combined score as a weighted average (0-1 range)

    Example:
        >>> scores = {"title": 0.9, "description": 0.7, "content": 0.5}
        >>> weights = {"title": 3.0, "description": 2.0, "content": 1.0}
        >>> combined = combine_field_scores(scores, weights)
        >>> 0.7 < combined < 0.8  # Weighted toward higher title score
        True
    """
    if not field_scores:
        return 0.0

    if weights is None:
        weights = DEFAULT_FIELD_WEIGHTS

    total_weight = 0.0
    weighted_sum = 0.0

    for field, score in field_scores.items():
        # Get weight for this field, default to 1.0 if not specified
        field_weight = weights.get(field, 1.0)

        # Add to weighted sum and total weight
        weighted_sum += score * field_weight
        total_weight += field_weight

    if total_weight == 0.0:
        return 0.0

    # Return weighted average
    return weighted_sum / total_weight
