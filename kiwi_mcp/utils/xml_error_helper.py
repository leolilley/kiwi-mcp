"""
Helper utilities for analyzing and improving XML parsing errors.
"""

import re
from typing import Dict, List, Optional, Tuple


def extract_line_column_from_parse_error(error_msg: str) -> Optional[Tuple[int, int]]:
    """
    Extract line and column numbers from ParseError message.
    
    ParseError messages typically look like:
    - "not well-formed (invalid token): line 392, column 44"
    - "syntax error: line 10, column 5"
    
    Returns:
        Tuple of (line_number, column_number) or None if not found
    """
    # Pattern to match "line X, column Y"
    pattern = r'line\s+(\d+),\s+column\s+(\d+)'
    match = re.search(pattern, error_msg, re.IGNORECASE)
    
    if match:
        line = int(match.group(1))
        column = int(match.group(2))
        return (line, column)
    
    return None


def extract_context_lines(xml_content: str, line_num: int, context_lines: int = 2) -> Dict[str, any]:
    """
    Extract context around a problematic line.
    
    Args:
        xml_content: The XML content as a string
        line_num: The line number where the error occurred (1-indexed)
        context_lines: Number of lines before/after to include
    
    Returns:
        Dict with:
        - 'problematic_line': The line with the error
        - 'line_number': Line number
        - 'context_before': List of lines before
        - 'context_after': List of lines after
        - 'column': Column number if provided
    """
    lines = xml_content.split('\n')
    total_lines = len(lines)
    
    # Convert to 0-indexed
    line_idx = line_num - 1
    
    if line_idx < 0 or line_idx >= total_lines:
        return {
            'problematic_line': '',
            'line_number': line_num,
            'context_before': [],
            'context_after': [],
        }
    
    problematic_line = lines[line_idx]
    
    # Get context before
    start_idx = max(0, line_idx - context_lines)
    context_before = lines[start_idx:line_idx]
    
    # Get context after
    end_idx = min(total_lines, line_idx + context_lines + 1)
    context_after = lines[line_idx + 1:end_idx]
    
    return {
        'problematic_line': problematic_line,
        'line_number': line_num,
        'context_before': context_before,
        'context_after': context_after,
    }


def detect_problematic_characters(line: str, column: Optional[int] = None) -> List[Dict[str, any]]:
    """
    Detect unescaped special characters in a line.
    
    Args:
        line: The line to analyze
        column: Optional column number where error occurred
    
    Returns:
        List of dicts with:
        - 'character': The problematic character
        - 'position': Character position (0-indexed)
        - 'pattern': Detected pattern type
        - 'suggestion': Suggested fix
    """
    issues = []
    
    # Pattern detection regexes
    patterns = [
        # Comparison operators: >80%, <100ms
        (r'([<>])\d+%?', 'comparison_operator'),
        # Arrows: ->, =>
        (r'->', 'arrow'),
        (r'=>', 'arrow'),
        # Generic types: Dict[str, Any], List[T]
        (r'\[[^\]]*\]', 'generic_type'),
        # Ampersand: & (not part of entity)
        (r'&(?!lt;|gt;|amp;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', 'ampersand'),
    ]
    
    for pattern, pattern_type in patterns:
        for match in re.finditer(pattern, line):
            start_pos = match.start()
            char = match.group(0)
            
            # Skip if this is inside a CDATA section
            # Simple check: count CDATA markers before this position
            before_text = line[:start_pos]
            cdata_opens = before_text.count('<![CDATA[')
            cdata_closes = before_text.count(']]>')
            if cdata_opens > cdata_closes:
                continue  # Inside CDATA, skip
            
            # Skip if already escaped
            if char.startswith('&') and char.endswith(';'):
                continue
            
            suggestion = _generate_suggestion(char, pattern_type)
            
            issues.append({
                'character': char,
                'position': start_pos,
                'pattern': pattern_type,
                'suggestion': suggestion,
            })
    
    # Also check for standalone < and > that aren't part of tags
    # This is more complex - we need to check if they're inside tags
    standalone_lt = re.finditer(r'<(?![!/?]?[a-zA-Z])', line)
    for match in standalone_lt:
        # Check if it's not part of a tag
        before = line[:match.start()]
        after = line[match.start():]
        
        # Simple heuristic: if there's no > before the next tag start, it might be problematic
        if not re.match(r'^<[^>]*>', after):
            issues.append({
                'character': '<',
                'position': match.start(),
                'pattern': 'standalone_lt',
                'suggestion': '&lt;',
            })
    
    # Check for standalone > that aren't part of tags
    # Use a simpler approach: find > that aren't immediately after <tag
    for i, char in enumerate(line):
        if char == '>':
            # Check if this > is part of a tag by looking backwards
            # Look for < followed by tag name before this >
            before = line[max(0, i-50):i]  # Check last 50 chars
            # If we find <tag> pattern, skip (it's a closing tag)
            # If we find <tag with no >, it might be part of opening tag, skip
            # Otherwise, it's likely a standalone >
            if not re.search(r'<[a-zA-Z][^>]*$', before):
                # Check if there's a < somewhere before that might make this part of a tag
                # Simple check: if there's <tag> before this, it's likely a closing tag
                if not re.search(r'<[a-zA-Z][^>]*>', line[:i]):
                    issues.append({
                        'character': '>',
                        'position': i,
                        'pattern': 'standalone_gt',
                        'suggestion': '&gt;',
                    })
    
    return issues


def _generate_suggestion(char: str, pattern_type: str) -> str:
    """Generate a suggestion for fixing a problematic character."""
    if pattern_type == 'comparison_operator':
        if char.startswith('>'):
            return char.replace('>', '&gt;', 1)
        elif char.startswith('<'):
            return char.replace('<', '&lt;', 1)
    elif pattern_type == 'arrow':
        if '->' in char:
            return char.replace('->', '-&gt;')
        elif '=>' in char:
            return char.replace('=>', '=&gt;')
    elif pattern_type == 'ampersand':
        return char.replace('&', '&amp;')
    elif pattern_type == 'standalone_lt':
        return '&lt;'
    elif pattern_type == 'standalone_gt':
        return '&gt;'
    
    # Default: escape the character
    if char == '<':
        return '&lt;'
    elif char == '>':
        return '&gt;'
    elif char == '&':
        return '&amp;'
    
    return char


def format_error_with_context(
    error_msg: str,
    xml_content: str,
    file_path: Optional[str] = None
) -> str:
    """
    Format a ParseError with helpful context and suggestions.
    
    Args:
        error_msg: The original ParseError message
        xml_content: The XML content that failed to parse
        file_path: Optional file path for the directive
    
    Returns:
        Formatted error message with context and suggestions
    """
    # Extract line/column from error
    line_col = extract_line_column_from_parse_error(error_msg)
    
    if not line_col:
        # Can't extract line info, return basic error
        return (
            f"Invalid directive XML: {error_msg}\n"
            f"Hint: Check for unescaped < > & characters. Use CDATA for special chars."
        )
    
    line_num, column = line_col
    
    # Get context
    context = extract_context_lines(xml_content, line_num, context_lines=2)
    problematic_line = context['problematic_line']
    
    # Detect issues
    issues = detect_problematic_characters(problematic_line, column)
    
    # Build error message
    parts = [
        f"Invalid directive XML at line {line_num}, column {column}",
        f"Error: {error_msg}",
        "",
        "Problematic line:",
        f"  {line_num:4d} | {problematic_line}",
    ]
    
    # Add context
    if context['context_before']:
        parts.append("")
        parts.append("Context (before):")
        for i, line in enumerate(context['context_before']):
            line_no = line_num - len(context['context_before']) + i
            parts.append(f"  {line_no:4d} | {line}")
    
    if context['context_after']:
        parts.append("")
        parts.append("Context (after):")
        for i, line in enumerate(context['context_after']):
            line_no = line_num + 1 + i
            parts.append(f"  {line_no:4d} | {line}")
    
    # Add suggestions
    if issues:
        parts.append("")
        parts.append("Detected issues and suggestions:")
        for issue in issues[:3]:  # Limit to first 3 issues
            char = issue['character']
            suggestion = issue['suggestion']
            pattern = issue['pattern']
            
            # Format suggestion
            if pattern == 'comparison_operator':
                parts.append(f"  - Found comparison operator '{char}' → use '{suggestion}'")
            elif pattern == 'arrow':
                parts.append(f"  - Found arrow '{char}' → use '{suggestion}'")
            elif pattern == 'ampersand':
                parts.append(f"  - Found unescaped '&' → use '&amp;'")
            else:
                parts.append(f"  - Found '{char}' at position {issue['position']} → use '{suggestion}'")
        
        if len(issues) > 3:
            parts.append(f"  ... and {len(issues) - 3} more issue(s)")
    
    parts.append("")
    parts.append("Solutions:")
    parts.append("  1. Escape special characters: < → &lt;, > → &gt;, & → &amp;")
    parts.append("  2. Wrap content in CDATA: <action><![CDATA[content with < > &]]></action>")
    parts.append("  3. For arrows: -> → -&gt;")
    
    if file_path:
        parts.append("")
        parts.append(f"File: {file_path}")
    
    return "\n".join(parts)
