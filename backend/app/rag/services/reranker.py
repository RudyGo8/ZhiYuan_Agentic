'''
@create_time: 2026/4/27 下午4:00
@Author: GeChao
@File: reranker.py
'''
import os
import requests


def rerank_documents(query: str, docs: list[dict], max_docs: int = 10):
    # rerank 重排：让模型再一次生成相关性分数
    rerank_api_key = os.getenv("RERANK_API_KEY")
    rerank_model_name = os.getenv("RERANK_MODEL")
    rerank_host = os.getenv("RERANK_BINDING_HOST")

    results = docs
    meta = {
        "rerank_enabled": False,
        "rerank_applied": False,
        "rerank_model": None,
        "rerank_endpoint": None,
        "rerank_error": None,
    }

    if rerank_api_key and rerank_model_name and rerank_host and results:
        meta["rerank_enabled"] = True
        try:
            # 拿前 10 条，而且每文本块只取前 1000 字符
            rerank_docs = [r["text"][:1000] for r in results[:max_docs]]
            rerank_response = requests.post(
                rerank_host,
                headers={
                    "Authorization": f"Bearer {rerank_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": rerank_model_name,
                    "query": query,
                    "documents": rerank_docs
                },
                timeout=30
            )
            rerank_response.raise_for_status()
            rerank_data = rerank_response.json()

            reranked = rerank_data.get("results", [])
            if reranked:
                rerank_scores = {doc["index"]: doc["relevance_score"] for doc in reranked}
                for i, r in enumerate(results[:max_docs]):
                    r["rerank_score"] = rerank_scores.get(i, 0.0)
                results = results[:max_docs]
                results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
                meta["rerank_applied"] = True
                meta["rerank_model"] = rerank_model_name
                meta["rerank_endpoint"] = rerank_host
        except Exception as e:
            meta["rerank_error"] = str(e)
    return results, meta