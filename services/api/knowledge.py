"""Small deterministic BM25 retriever over the attributed reference corpus."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .brief_schemas import PatternMatch, PatternSearchRequest, PatternSearchResponse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_PATH = ROOT / "data" / "knowledge" / "incident_patterns.json"
TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "while",
    "with",
}


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOP_WORDS]


def _document_text(pattern: dict[str, Any]) -> str:
    source_metadata = " ".join(
        f"{source['title']} {source['publisher']} {source['locator']}"
        for source in pattern["sources"]
    )
    return " ".join(
        [
            pattern["title"],
            pattern["pattern_summary"],
            " ".join(pattern["signals"]),
            " ".join(pattern["review_prompts"]),
            source_metadata,
        ]
    )


class IncidentPatternIndex:
    """In-memory local index with deterministic BM25 ranking."""

    def __init__(self, corpus_path: Path | None = None) -> None:
        self.corpus_path = corpus_path or DEFAULT_CORPUS_PATH
        raw = self.corpus_path.read_bytes()
        self.corpus_sha256 = hashlib.sha256(raw).hexdigest()
        self.corpus: dict[str, Any] = json.loads(raw.decode("utf-8"))
        self.patterns: list[dict[str, Any]] = self.corpus["patterns"]
        self._validate_corpus()
        self.documents = [tokenize(_document_text(pattern)) for pattern in self.patterns]
        self.term_frequencies = [Counter(document) for document in self.documents]
        self.document_lengths = [len(document) for document in self.documents]
        self.average_document_length = sum(self.document_lengths) / len(self.document_lengths)
        self.document_frequency = Counter(
            token for document in self.documents for token in set(document)
        )

    def _validate_corpus(self) -> None:
        if self.corpus.get("data_classification") != "REFERENCE":
            raise ValueError("knowledge corpus must be classified REFERENCE")
        if not self.patterns:
            raise ValueError("knowledge corpus must include at least one pattern")
        seen: set[str] = set()
        for pattern in self.patterns:
            pattern_id = pattern["pattern_id"]
            if pattern_id in seen:
                raise ValueError(f"duplicate pattern_id: {pattern_id}")
            seen.add(pattern_id)
            if pattern.get("classification") != "REFERENCE":
                raise ValueError(f"pattern {pattern_id} must be classified REFERENCE")
            if not pattern.get("sources"):
                raise ValueError(f"pattern {pattern_id} has no sources")
            for source in pattern["sources"]:
                if not source.get("url", "").startswith("https://"):
                    raise ValueError(f"pattern {pattern_id} has a non-HTTPS source")

    def metadata(self) -> dict[str, Any]:
        source_ids = sorted(
            {
                source["source_id"]
                for pattern in self.patterns
                for source in pattern["sources"]
            }
        )
        return {
            "data_classification": "REFERENCE",
            "corpus_name": self.corpus["corpus_name"],
            "corpus_version": self.corpus["corpus_version"],
            "corpus_sha256": self.corpus_sha256,
            "pattern_count": len(self.patterns),
            "source_ids": source_ids,
            "retrieval_method": "LOCAL_BM25",
            "generative_model_used": False,
            "scope_note": self.corpus["scope_note"],
            "licensing_note": self.corpus["licensing_note"],
        }

    def search(self, request: PatternSearchRequest) -> PatternSearchResponse:
        # Context signals are intentionally repeated once to make structured
        # evidence modestly more influential than free-form prose.
        query_tokens = tokenize(request.query)
        signal_tokens = tokenize(" ".join(request.context_signals))
        weighted_query = query_tokens + signal_tokens + signal_tokens
        query_terms = sorted(set(weighted_query))
        corpus_size = len(self.documents)
        k1 = 1.5
        b = 0.75
        ranked: list[tuple[float, int, list[str]]] = []

        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            matched: list[str] = []
            length_normalizer = 1 - b + b * (
                self.document_lengths[index] / self.average_document_length
            )
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if frequency == 0:
                    continue
                matched.append(term)
                document_frequency = self.document_frequency[term]
                inverse_document_frequency = math.log(
                    1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                score += inverse_document_frequency * (
                    frequency * (k1 + 1)
                    / (frequency + k1 * length_normalizer)
                )
            if score > 0:
                ranked.append((score, index, matched))

        ranked.sort(key=lambda item: (-item[0], self.patterns[item[1]]["pattern_id"]))
        results = []
        for score, index, matched in ranked[: request.top_k]:
            pattern = self.patterns[index]
            results.append(
                PatternMatch(
                    **pattern,
                    score=round(score, 6),
                    matched_terms=matched,
                )
            )

        return PatternSearchResponse(
            data_classification="REFERENCE",
            corpus_name=self.corpus["corpus_name"],
            corpus_version=self.corpus["corpus_version"],
            corpus_sha256=self.corpus_sha256,
            retrieval_method="LOCAL_BM25",
            generative_model_used=False,
            query=request.query,
            results=results,
            corpus_scope_note=self.corpus["scope_note"],
            licensing_note=self.corpus["licensing_note"],
        )
