"""Deterministic paragraph-first splitting; bounds are characters, not tokens."""

import re

CHUNKER_VERSION = "paragraph-char-v1"


def split_text(text: str, *, max_chars: int = 1000, overlap: int = 100) -> list[str]:
    if max_chars < 100 or not 0 <= overlap < max_chars // 2:
        raise ValueError("Invalid chunk size/overlap")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    chunks = []
    while text:
        end = min(len(text), max_chars)
        if end < len(text):
            # Prefer a complete paragraph, then a sentence, in the latter half.
            boundaries = [m.end() for m in re.finditer(r"\n\n|[。！？.!?]\s*", text[:end])
                          if m.end() >= max_chars // 2]
            if boundaries:
                end = boundaries[-1]
        chunk = text[:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        text = text[end - overlap:].lstrip()
    return chunks
