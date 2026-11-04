import re
from typing import Any, Dict, List

class RecursiveCharacterTextSplitter:
    """
    Splits text recursively using semantic boundaries (paragraphs, sentences, words)
    while maintaining a sliding character overlap to preserve context across chunk seams.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        separators: List[str] = None
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly smaller than chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Splits raw text into a list of strings within chunk_size boundaries."""
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        if not separators:
            # Fallback to hard character slicing if no separators remain
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        remaining_separators = separators[1:]

        # Find the highest-priority separator present in text
        if separator != "" and separator not in text:
            return self._split(text, remaining_separators)

        splits = text.split(separator) if separator != "" else list(text)

        chunks: List[str] = []
        current_doc: List[str] = []
        total_len = 0

        for s in splits:
            s_len = len(s) + (len(separator) if current_doc else 0)

            # If a single component exceeds chunk_size, break it recursively
            if len(s) > self.chunk_size:
                if current_doc:
                    combined = separator.join(current_doc).strip()
                    if combined:
                        chunks.append(combined)
                    current_doc = []
                    total_len = 0
                sub_chunks = self._split(s, remaining_separators)
                chunks.extend(sub_chunks)
                continue

            if total_len + s_len > self.chunk_size and current_doc:
                combined = separator.join(current_doc).strip()
                if combined:
                    chunks.append(combined)

                # Build sliding overlap from tail of current_doc
                overlap_doc: List[str] = []
                overlap_len = 0
                for item in reversed(current_doc):
                    item_cost = len(item) + (len(separator) if overlap_doc else 0)
                    if overlap_len + item_cost <= self.chunk_overlap:
                        overlap_doc.insert(0, item)
                        overlap_len += item_cost
                    else:
                        break

                current_doc = overlap_doc
                total_len = overlap_len

            current_doc.append(s)
            total_len += s_len

        if current_doc:
            combined = separator.join(current_doc).strip()
            if combined and (not chunks or chunks[-1] != combined):
                chunks.append(combined)

        return [c for c in chunks if c.strip()]

    def split_document_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits text with page-level provenance.
        Input: [{'page': 1, 'text': '...'}]
        Output: list of dicts with content, token_count, and metadata.
        """
        chunks: List[Dict[str, Any]] = []
        global_index = 0

        for page_data in pages:
            page_num = page_data.get('page', 1)
            raw_text = page_data.get('text', '')
            page_chunks = self.split_text(raw_text)

            for chunk_str in page_chunks:
                # Approximate token count: standard word count proxy
                words = chunk_str.split()
                token_count = max(1, len(words))

                start_char = raw_text.find(chunk_str) if raw_text else 0
                end_char = start_char + len(chunk_str) if start_char != -1 else len(chunk_str)

                chunks.append({
                    'chunk_index': global_index,
                    'content': chunk_str,
                    'token_count': token_count,
                    'metadata': {
                        'page': page_num,
                        'start_char': max(0, start_char),
                        'end_char': end_char,
                        'char_count': len(chunk_str),
                    }
                })
                global_index += 1

        return chunks

