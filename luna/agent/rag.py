"""人设知识库 RAG（v5 P2 轻量版）：markdown 知识文件 + 关键词检索注入。

刻意不上向量库/Embedding：直播人设知识的量级（几 KB～几十 KB）用
「CJK 2-gram + 英数词」关键词打分检索足够准，且零新依赖、零索引维护。
知识目录（默认 knowledge/）放 markdown 文件，主播在 WebUI 里直接编辑；
文件 mtime 变化自动重载。

检索：query 分词 → 每块命中计分 → top_k 块按 max_chars 拼接注入
system prompt（AgentRuntime 调用，见 _build_system_prompt）。
"""

import re
from pathlib import Path

from luna.infra.my_log import logger

# 分块目标长度（字符）：heading 开新块，段落累积到这个量级就切块
CHUNK_TARGET_CHARS = 400
# 检索词最短长度：单字命中率太高噪声大
MIN_TERM_LEN = 2


def tokenize(query: str) -> list:
    """查询分词：CJK 连续段切 2-gram，英文/数字按词。"""
    terms = set()
    for word in re.findall(r"[A-Za-z0-9]+", query):
        if len(word) >= MIN_TERM_LEN:
            terms.add(word.lower())
    for seq in re.findall(r"[\u4e00-\u9fff]+", query):
        if len(seq) == 1:
            terms.add(seq)
            continue
        for i in range(len(seq) - 1):
            terms.add(seq[i : i + 2])
    return [t for t in terms if len(t) >= MIN_TERM_LEN]


class KnowledgeBase:
    def __init__(self, knowledge_dir: str):
        self.dir = Path(knowledge_dir)
        self.chunks: list = []  # [{"source": 文件名, "title": 首个标题, "text": 正文}]
        self._mtimes: dict = {}

    def reload_if_changed(self) -> None:
        """目录内 markdown 文件 mtime 变化即重载（没建目录/没文件则静默为空）。"""
        if not self.dir.is_dir():
            self.chunks = []
            self._mtimes = {}
            return
        mtimes = {p.name: p.stat().st_mtime for p in self.dir.glob("*.md")}
        if mtimes != self._mtimes:
            self.chunks = []
            for name, _ in sorted(mtimes.items()):
                try:
                    text = (self.dir / name).read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"知识文件 {name} 读取失败：{e}")
                    continue
                self.chunks.extend(self._chunk_file(name, text))
            self._mtimes = mtimes
            logger.debug(f"知识库已加载 {len(self.chunks)} 块（{len(mtimes)} 个文件）")

    @staticmethod
    def _chunk_file(source: str, text: str) -> list:
        chunks = []
        title = source
        buffer: list = []
        size = 0

        def flush():
            nonlocal buffer, size
            body = "\n".join(buffer).strip()
            if body:
                chunks.append({"source": source, "title": title, "text": body[: CHUNK_TARGET_CHARS * 2]})
            buffer, size = [], 0

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                title = stripped.lstrip("#").strip() or source
                buffer.append(stripped)
                size = len(stripped)
                continue
            buffer.append(line)
            size += len(line)
            if size >= CHUNK_TARGET_CHARS:
                flush()
        flush()
        return chunks

    def retrieve(self, query: str, top_k: int = 3, max_chars: int = 600) -> str:
        """检索与 query 最相关的知识片段；无命中返回空串。"""
        self.reload_if_changed()
        terms = tokenize(query)
        if not terms or not self.chunks:
            return ""
        scored = []
        for chunk in self.chunks:
            haystack = chunk["text"]
            title = chunk["title"]
            score = sum(haystack.count(term) + title.count(term) * 2 for term in terms)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: -item[0])
        picked, used = [], 0
        for _, chunk in scored[: max(1, top_k)]:
            piece = f"【{chunk['source']}·{chunk['title']}】{chunk['text']}"
            if used + len(piece) > max_chars and picked:
                break
            picked.append(piece[: max_chars - used])
            used += len(picked[-1])
            if used >= max_chars:
                break
        return "\n---\n".join(picked)

    def status(self) -> dict:
        self.reload_if_changed()
        by_source: dict = {}
        for chunk in self.chunks:
            by_source[chunk["source"]] = by_source.get(chunk["source"], 0) + 1
        return {"dir": str(self.dir), "files": sorted(self._mtimes), "chunks": len(self.chunks), "per_file": by_source}
