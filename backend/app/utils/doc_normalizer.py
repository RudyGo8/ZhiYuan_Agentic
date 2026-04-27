'''
@create_time: 2026/4/27 下午6:21
@Author: GeChao
@File: doc_normalizer.py
'''
from typing import Any


def normalize_doc(doc: Any) -> dict:
    """
    将单个检索结果统一转换成 dict。

    目标格式：
    {
        "text": "...",
        ...
    }
    """

    if isinstance(doc, dict):
        return doc

    if isinstance(doc, str):
        return {
            "text": doc
        }

    return {
        "text": str(doc)
    }


def normalize_docs(docs: Any) -> list[dict]:
    """
    将检索结果统一转换成 list[dict]。
    """

    if not docs:
        return []

    if isinstance(docs, dict):
        docs = docs.get("docs") or docs.get("results") or []

    if isinstance(docs, str):
        return [{"text": docs}]

    return [normalize_doc(doc) for doc in docs]