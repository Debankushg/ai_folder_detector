"""Tiny local RAG: chunk source files and retrieve with TF-IDF (no external API needed)."""
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from ..analysis.file_utils import iter_files, read_text

CHUNK_LINES = 40


OVERLAP = 8


TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def _tokens(text: str):
    out = []
    for t in TOKEN.findall(text):
        out.append(t.lower())
        # split camelCase / snake_case so "getUser" matches "get user"
        out += [w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", t)]
    return out


class CodeIndex:
    def __init__(self, root: Path):
        self.root = root
        self.chunks: list[dict] = []
        for p in iter_files(root):
            lines = read_text(p).splitlines()
            rel = str(p.relative_to(root))
            step = CHUNK_LINES - OVERLAP
            for i in range(0, max(len(lines), 1), step):
                text = "\n".join(lines[i:i + CHUNK_LINES]).strip()
                if text:
                    self.chunks.append({"file": rel, "start": i + 1, "text": text})
        self.vec = None
        if self.chunks:
            self.vec = TfidfVectorizer(tokenizer=_tokens, lowercase=False, token_pattern=None)
            self.matrix = self.vec.fit_transform(c["file"] + "\n" + c["text"] for c in self.chunks)

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.vec:
            return []
        scores = linear_kernel(self.vec.transform([query]), self.matrix).ravel()
        top = scores.argsort()[::-1][:k]
        return [{**self.chunks[i], "score": round(float(scores[i]), 3)} for i in top if scores[i] > 0]
