# -*- coding: UTF-8 -*-
"""@File    : openai_model.py
@Description : 本地资料向量化后检索问答。直接调用 OpenAI 兼容接口 + faiss，不再依赖 langchain。
"""
import os
import zipfile

import faiss
import numpy as np
from openai import OpenAI
from PyPDF2 import PdfReader

from utils.chat_with_file.chat_mode.chat_model import Chat_model
from utils.my_log import logger

EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_BATCH_SIZE = 64
TEXT_SUFFIXES = (".txt", ".tex", ".md")
NO_MATCH_REPLY = "没有获取到匹配结果。"


class Openai_mode(Chat_model):
    def __init__(self, data):
        super().__init__(data)

        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.openai_api)
        self.chunks = []
        self.index = None

        logger.info(f"chat_with_file 数据文件：{self.data_path}")
        self.chunks = self._read_chunks()
        if not self.chunks:
            logger.error(f"chat_with_file 未能从 {self.data_path} 读取到文本，检索功能不可用")
            return

        logger.info(f"chat_with_file 共切分为 {len(self.chunks)} 块文本")
        vectors = self._embed(self.chunks)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def _read_chunks(self):
        chunks = []
        for dir_path, _, file_names in os.walk(self._extract_source_data()):
            for file_name in sorted(file_names):
                path = os.path.join(dir_path, file_name)
                if file_name.endswith(TEXT_SUFFIXES):
                    text = self._read_text_file(path)
                elif file_name.endswith(".pdf"):
                    text = self._read_pdf_file(path)
                else:
                    continue
                chunks.extend(self._split_text(text))
        return [chunk for chunk in chunks if chunk.strip()]

    def _extract_source_data(self):
        source_data = os.path.join(os.getcwd(), "data", "vector_base", "source_data")
        os.makedirs(source_data, exist_ok=True)

        with zipfile.ZipFile(self.data_path, "r") as zip_ref:
            # 压缩包由用户提供，先校验成员路径，避免 ../ 写到目标目录之外
            for member in zip_ref.namelist():
                target = os.path.abspath(os.path.join(source_data, member))
                if os.path.commonpath([target, source_data]) != source_data:
                    raise ValueError(f"数据压缩包内含越界路径：{member}")
            zip_ref.extractall(source_data)

        return source_data

    def _read_text_file(self, path):
        with open(path, "rb") as f:
            raw = f.read()
        for encoding in ("utf-8", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    def _read_pdf_file(self, path):
        try:
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.error(f"chat_with_file 解析 PDF 失败：{path}，{e}")
            return ""

    def _split_text(self, text):
        if not text or not text.strip():
            return []
        if len(text) <= self.chunk_size:
            return [text.strip()]

        pieces = text.split(self.separator) if self.separator else list(text)
        chunks = []
        current = ""
        for piece in pieces:
            candidate = current + self.separator + piece if current else piece
            if len(candidate) > self.chunk_size and current:
                chunks.append(current)
                current = current[-self.chunk_overlap :] if self.chunk_overlap > 0 else ""

            while len(piece) > self.chunk_size:
                chunks.append(piece[: self.chunk_size])
                piece = piece[self.chunk_size :]

            current = current + self.separator + piece if current else piece

        if current:
            chunks.append(current)
        return chunks

    def _embed(self, texts):
        vectors = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = [text or " " for text in texts[start : start + EMBEDDING_BATCH_SIZE]]
            response = self.client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            vectors.extend(item.embedding for item in response.data)

        array = np.asarray(vectors, dtype="float32")
        # 归一化后用内积索引，等价于余弦相似度
        norms = np.linalg.norm(array, axis=1, keepdims=True)
        return array / np.clip(norms, 1e-12, None)

    def _search(self, query):
        if self.index is None:
            return []
        k = min(self.local_max_query, len(self.chunks))
        _, indices = self.index.search(self._embed([query]), k)
        return [self.chunks[i] for i in indices[0] if 0 <= i < len(self.chunks)]

    def get_model_resp(self, content=""):
        docs = self._search(content)
        if not docs:
            return NO_MATCH_REPLY

        if self.chat_mode == "openai_vector_search":
            return docs[0]

        if self.chain_type != "stuff":
            logger.warning(f"chat_with_file 仅实现了 stuff 链，chain_type={self.chain_type} 按 stuff 处理")

        context = "\n\n".join(docs)
        prompt = f"{self.question_prompt}\n\ncontent：{context}\n\nquestion: {content}"
        response = self.client.chat.completions.create(
            model=self.openai_model_name,
            messages=[{"role": "user", "content": prompt}],
        )

        if self.show_token_cost:
            usage = response.usage
            logger.info(
                f"chat_with_file token 用量：输入 {usage.prompt_tokens}，输出 {usage.completion_tokens}，"
                f"合计 {usage.total_tokens}"
            )

        return response.choices[0].message.content
