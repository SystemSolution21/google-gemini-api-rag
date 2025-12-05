# src/utils/formatters.py
"""
Response formatting utilities.

Contains functions for formatting Gemini responses with citations
and other text processing utilities.
"""

import re
from typing import Optional

from google.genai import types


def format_response_with_citations(
    response: types.GenerateContentResponse,
    source_document_name: Optional[str] = None,
    file_path: Optional[str] = None,
) -> str:
    """Format Gemini's response text with citation links.

    Parameters
    ----------
    response : types.GenerateContentResponse
        The raw response object returned by Gemini.
    source_document_name : Optional[str]
        The filename of the source document to link citations to. If
        provided and file_path is None, inline and standalone citation
        patterns in the response text are replaced with Markdown links
        pointing to the corresponding PDF page in the `public` directory.
    file_path : Optional[str]
        Full path to the file (e.g., "user_id/session_id/filename.pdf").
        If provided, this takes precedence over source_document_name.
        Used for multi-user scenarios.

    Returns
    -------
    str
        The formatted response text, including a **Citations** section
        listing all citation metadata (source URI and index ranges) if
        available.
    """
    answer_text = response.text or ""

    # Determine the path to use for citations
    citation_path = file_path if file_path else source_document_name

    # Link page citations if source document is provided
    if citation_path and answer_text:
        # Pattern for ", p. X)" - inline citations with quotes
        answer_text = re.sub(
            r'",\s*p\.\s*(\d+)\)',
            rf'", [p. \1](/public/{citation_path}#page=\1))',
            answer_text,
        )
        # Pattern for (p. X) - standalone citations
        answer_text = re.sub(
            r"\(p\.\s*(\d+)\)",
            rf"([p. \1](/public/{citation_path}#page=\1))",
            answer_text,
        )
        # Pattern for ", p. X-Y)" - inline range citations
        answer_text = re.sub(
            r'",\s*p\.\s*(\d+)-(\d+)\)',
            rf'", [p. \1-\2](/public/{citation_path}#page=\1))',
            answer_text,
        )
        # Pattern for (p. X-Y) - standalone range citations
        answer_text = re.sub(
            r"\(p\.\s*(\d+)-(\d+)\)",
            rf"([p. \1-\2](/public/{citation_path}#page=\1))",
            answer_text,
        )

    citations = []
    if response.candidates and response.candidates[0].citation_metadata:
        citation_metadata = response.candidates[0].citation_metadata
        if citation_metadata.citations:
            citations.append("\n\n**Citations:**")
            for i, source in enumerate(citation_metadata.citations):
                citation_text = f"{i + 1}. "
                if source.uri:
                    citation_text += f"[{source.uri}]({source.uri})"
                else:
                    citation_text += "Source Document"

                if source.start_index is not None and source.end_index is not None:
                    citation_text += (
                        f" (Indexes: {source.start_index}-{source.end_index})"
                    )

                citations.append(citation_text)

    return answer_text + "\n".join(citations)
