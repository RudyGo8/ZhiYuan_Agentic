'''
@create_time: 2025/09/09
@Author: GeChao
@File: embedding_service.py
'''
import os
import re
import math
import threading
import requests
from collections import Counter
from app.config import BASE_URL, EMBEDDER, ARK_API_KEY


class EmbeddingService:
    def __init__(self):
        self.base_url = BASE_URL
        self.embedder = EMBEDDER
        self.api_key = ARK_API_KEY
        self.k1 = 1.5
        self.b = 0.75
        self._vocab = {}
        self._vocab_counter = 0
        self._doc_freq = Counter()
        self._total_docs = 0
        self._avg_doc_len = 0
        self._stats_lock = threading.Lock()

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            url = f"{self.base_url}/embeddings"
            data = {
                "model": self.embedder,
                "input": texts
            }
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return [item["embedding"] for item in result["data"]]
        except Exception as e:
            raise Exception(f"嵌入 API 调用失败: {str(e)}")

    def get_embedding(self, text: str) -> list[float]:
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else []

    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        tokens = []
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        english_pattern = re.compile(r'[a-zA-Z]+')
        i = 0
        while i < len(text):
            char = text[i]
            if chinese_pattern.match(char):
                tokens.append(char)
                i += 1
            elif english_pattern.match(char):
                match = english_pattern.match(text[i:])
                if match:
                    tokens.append(match.group())
                    i += len(match.group())
            else:
                i += 1
        return tokens

    def get_sparse_embedding(self, text: str) -> dict:
        tokens = self.tokenize(text)
        if not tokens:
            return {}
        doc_len = len(tokens)
        tf = Counter(tokens)
        sparse_vector = {}
        with self._stats_lock:
            total_docs = max(self._total_docs, 1)
            avg_doc_len = self._avg_doc_len if self._avg_doc_len > 0 else doc_len

            for token, freq in tf.items():
                if token not in self._vocab:
                    self._vocab[token] = self._vocab_counter
                    self._vocab_counter += 1
                idx = self._vocab[token]
                df = self._doc_freq.get(token, 0)
                # BM25 算法
                idf = math.log((total_docs + 1.0) / (df + 0.5)) + 1.0
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / max(avg_doc_len, 1))
                score = idf * numerator / denominator
                if score > 0:
                    sparse_vector[idx] = float(score)
        return sparse_vector

    def get_sparse_embeddings(self, texts: list[str]) -> list[dict]:
        tokenized_docs = [self.tokenize(text) for text in texts]
        with self._stats_lock:
            total_len = self._avg_doc_len * self._total_docs
            for tokens in tokenized_docs:
                if not tokens:
                    continue
                self._total_docs += 1
                total_len += len(tokens)
                for token in set(tokens):
                    self._doc_freq[token] += 1
                    if token not in self._vocab:
                        self._vocab[token] = self._vocab_counter
                        self._vocab_counter += 1
            self._avg_doc_len = total_len / self._total_docs if self._total_docs > 0 else 0
        return [self.get_sparse_embedding(text) for text in texts]


embedding_service = EmbeddingService()
