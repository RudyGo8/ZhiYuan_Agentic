import os
import json
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
import requests
from langchain.chat_models import init_chat_model

load_dotenv()

from app.utils.embedding_service import embedding_service
from app.utils.milvus_service import milvus_service
from app.config import (
    ARK_API_KEY, MODEL, BASE_URL,
    AUTO_MERGE_ENABLED, AUTO_MERGE_THRESHOLD, LEAF_RETRIEVE_LEVEL
)

# 配置参数解析
AUTO_MERGE_ENABLED = AUTO_MERGE_ENABLED.lower() == "true" if isinstance(AUTO_MERGE_ENABLED, str) else bool(AUTO_MERGE_ENABLED)
AUTO_MERGE_THRESHOLD = int(AUTO_MERGE_THRESHOLD) if AUTO_MERGE_THRESHOLD else 2
LEAF_RETRIEVE_LEVEL = int(LEAF_RETRIEVE_LEVEL) if LEAF_RETRIEVE_LEVEL else 3


def _get_default_model():
    return init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=ARK_API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )


def retrieve_documents(query: str, top_k: int = 5) -> dict:

    milvus_service.init_collection()
    dense_embedding = embedding_service.get_embedding(query)
    sparse_embedding = embedding_service.get_sparse_embedding(query)

    # 混合检索
    retrieval_mode = "hybrid"
    try:
        results = milvus_service.hybrid_search(dense_embedding, sparse_embedding, top_k * 2)
    except Exception:
        retrieval_mode = "dense"
        results = milvus_service.dense_search(dense_embedding, top_k * 2)

    # rerank 重排：让模型再一次生成相关性分数
    rerank_enabled = False
    rerank_applied = False
    rerank_model = None
    rerank_endpoint = None
    rerank_error = None

    rerank_api_key = os.getenv("RERANK_API_KEY")
    rerank_model_name = os.getenv("RERANK_MODEL")
    rerank_host = os.getenv("RERANK_BINDING_HOST")

    if rerank_api_key and rerank_model_name and rerank_host and results:
        rerank_enabled = True
        try:
            # 拿前 10 条，而且每文本块只取前 1000 字符
            rerank_docs = [r["text"][:1000] for r in results[:10]]
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
                for i, r in enumerate(results[:10]):
                    r["rerank_score"] = rerank_scores.get(i, 0.0)
                results = results[:10]
                results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
                rerank_applied = True
                rerank_model = rerank_model_name
                rerank_endpoint = rerank_host
        except Exception as e:
            rerank_error = str(e)

    # 自动合并 小段 -> 大段  同父去重
    auto_merge_enabled = AUTO_MERGE_ENABLED
    auto_merge_applied = False
    auto_merge_replaced_chunks = 0
    auto_merge_steps = 0

    if auto_merge_enabled and results:
        try:
            from app.utils.parent_chunk_store import parent_chunk_store
            merged_results = []
            used_indices = set()

            for i, r in enumerate(results):
                if i in used_indices:
                    continue

                chunk_id = r.get("chunk_id", "")
                parent_id = r.get("parent_chunk_id", "")

                # 如果存在父分块ID，尝试获取父分块内容
                if parent_id:
                    parent_doc = parent_chunk_store.get_chunk(parent_id)
                    if parent_doc:
                        # 替换为父分块内容，提供更完整的上下文
                        r["text"] = parent_doc.get("text", r["text"])
                        r["parent_retrieved"] = True
                        # 标记已合并的子分块
                        for j in range(i + 1, len(results)):
                            if results[j].get("parent_chunk_id") == parent_id:
                                used_indices.add(j)
                        auto_merge_applied = True
                        auto_merge_steps = max(auto_merge_steps, 1)
                        auto_merge_replaced_chunks += 1

                merged_results.append(r)

            results = merged_results[:top_k]
        except Exception:
            pass

    for idx, r in enumerate(results):
        r["final_rank"] = idx + 1

    # 构建元数据
    meta = {
        "retrieval_mode": retrieval_mode,
        "candidate_k": len(results),
        "leaf_retrieve_level": LEAF_RETRIEVE_LEVEL,
        "auto_merge_enabled": auto_merge_enabled,
        "auto_merge_applied": auto_merge_applied,
        "auto_merge_threshold": AUTO_MERGE_THRESHOLD,
        "auto_merge_replaced_chunks": auto_merge_replaced_chunks,
        "auto_merge_steps": auto_merge_steps,
        "rerank_enabled": rerank_enabled,
        "rerank_applied": rerank_applied,
        "rerank_model": rerank_model,
        "rerank_endpoint": rerank_endpoint,
        "rerank_error": rerank_error,
    }

    return {"docs": results[:top_k], "meta": meta}


# 查询扩展策略
# 退步问题扩展策略
def step_back_expand(query: str) -> dict:
    try:
        from langchain.chat_models import init_chat_model
        model = _get_default_model()

        prompt = f"""请根据用户问题生成一个更通用的退步问题（Step-back），以及对应的通用答案。
用户问题：{query}

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "step_back_question": "更通用的退步问题",
    "step_back_answer": "通用答案",
    "expanded_query": "可用于检索的扩展查询"
}}"""

        response = model.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "step_back_question": result.get("step_back_question", query),
                "step_back_answer": result.get("step_back_answer", ""),
                "expanded_query": result.get("expanded_query", query)
            }
    except Exception as e:
        pass

    return {
        "step_back_question": query,
        "step_back_answer": "",
        "expanded_query": query
    }


# 假设文档生成策略
def generate_hypothetical_document(query: str) -> str:
    try:
        from langchain.chat_models import init_chat_model
        model = _get_default_model()

        prompt = f"""请生成一个假设性的文档内容，用于HyDE检索。
这个文档应该回答以下问题：{query}

请直接生成文档内容，不要添加解释。"""

        response = model.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception:
        return query
