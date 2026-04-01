"""
RAG 工具模块 - 底层检索实现
================================================================================
本模块提供 RAG Pipeline 所需的核心检索功能

核心函数:
    1. retrieve_documents: 文档检索 (Hybrid Search + Re-rank + Auto-merging)
    2. step_back_expand: Step-back 查询扩展
    3. generate_hypothetical_document: HyDE 假设文档生成

检索流程:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Step 1: 向量化                                                         │
    │         dense_embedding = get_embedding(query)                       │
    │         sparse_embedding = get_sparse_embedding(query)                │
    │                                                                         │
    │ Step 2: Hybrid Search                                                 │
    │         milvus_service.hybrid_search(dense, sparse, top_k*2)         │
    │         → RRF 融合密集向量和稀疏向量结果                               │
    │                                                                         │
    │ Step 3: Re-rank (可选)                                                │
    │         调用外部重排序 API                                             │
    │         → 按相关性分数重新排序                                         │
    │                                                                         │
    │ Step 4: Auto-merging                                                  │
    │         检查 parent_chunk_id                                          │
    │         → 替换为父分块内容，提升上下文完整性                           │
    │                                                                         │
    │ Step 5: 返回结果                                                       │
    │         {"docs": [...], "meta": {...}}                                │
    └─────────────────────────────────────────────────────────────────────────┘
================================================================================
"""
import os
import json
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

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
    """获取默认 LLM 模型 (用于 step-back 和 HyDE)"""
    return init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=ARK_API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )


# ===============================================================================
# [核心函数] retrieve_documents - 文档检索
# ===============================================================================
def retrieve_documents(query: str, top_k: int = 5) -> dict:
    """
    ================================================================================
    [核心函数] retrieve_documents - 文档检索
    ================================================================================
    功能: 对用户查询进行知识库检索，返回相关文档
    
    完整检索流程:
        ┌─────────────────────────────────────────────────────────────────────┐
        │ Step 1: 向量化                                                       │
        │         ├─ dense_embedding: 语义向量 (text-embedding-v2)            │
        │         └─ sparse_embedding: 稀疏向量 (BM25 变体)                  │
        │                                                                         │
        │ Step 2: Hybrid Search                                               │
        │         ├─ 密集向量搜索 (HNSW 索引)                                  │
        │         ├─ 稀疏向量搜索 (SPARSE_INVERTED_INDEX)                    │
        │         └─ RRF 融合: score = Σ 1/(rank + k=60)                     │
        │                                                                         │
        │ Step 3: Re-rank (可选)                                              │
        │         ├─ 调用外部重排序 API                                        │
        │         └─ 按相关性分数排序                                          │
        │                                                                         │
        │ Step 4: Auto-merging                                                │
        │         ├─ 检查 parent_chunk_id                                     │
        │         ├─ 替换为父分块内容                                          │
        │         └─ 合并相关片段，减少冗余                                     │
        │                                                                         │
        │ Step 5: 返回结果                                                    │
        │         └─ {"docs": [...], "meta": {...}}                          │
        └─────────────────────────────────────────────────────────────────────┘
    
    参数:
        - query: 用户查询
        - top_k: 返回文档数量 (默认 5，实际检索 top_k*2 以保留候选)
    
    返回:
        {
            "docs": [
                {
                    "text": "文档内容",
                    "filename": "文件名",
                    "page_number": 1,
                    "chunk_id": "chunk_id",
                    "parent_chunk_id": "父分块ID",
                    "score": 0.95,
                    "rrf_rank": 1
                },
                ...
            ],
            "meta": {
                "retrieval_mode": "hybrid",
                "candidate_k": 10,
                "leaf_retrieve_level": 3,
                "auto_merge_enabled": true,
                "auto_merge_applied": true,
                "rerank_enabled": true,
                "rerank_applied": true,
                ...
            }
        }
    ================================================================================
    """
    # ========== Step 0: 初始化 Milvus Collection ==========
    milvus_service.init_collection()
    
    # ========== Step 1: 向量化 (密集 + 稀疏) ==========
    dense_embedding = embedding_service.get_embedding(query)
    sparse_embedding = embedding_service.get_sparse_embedding(query)
    
    # ========== Step 2: Hybrid Search ==========
    # 尝试混合搜索，如果失败则回退到密集搜索
    try:
        results = milvus_service.hybrid_search(dense_embedding, sparse_embedding, top_k * 2)
    except Exception:
        results = milvus_service.dense_search(dense_embedding, top_k * 2)
    
    # ========== Step 3: Re-rank (可选) ==========
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
    
    # ========== Step 4: Auto-merging (自动合并父分块) ==========
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
    
    # ========== Step 5: 添加 RRF 排名 ==========
    for idx, r in enumerate(results):
        r["rrf_rank"] = idx + 1
    
    # ========== Step 6: 构建元数据 ==========
    meta = {
        "retrieval_mode": "hybrid" if hasattr(milvus_service, 'sparse_embedding') else "dense",
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


# ===============================================================================
# Step-back 查询扩展
# ===============================================================================
def step_back_expand(query: str) -> dict:
    """
    ================================================================================
    [辅助函数] step_back_expand - Step-back 查询扩展
    ================================================================================
    功能: 将具体问题泛化为更通用的退步问题，再用于检索
    
    示例:
        输入: "Transformer 的注意力机制是如何工作的？"
        输出: {
            "step_back_question": "什么是 Transformer 的注意力机制？",
            "step_back_answer": "注意力机制是...",
            "expanded_query": "Transformer 注意力机制 工作原理 深度学习"
        }
    
    实现: 调用 LLM 生成退步问题和答案
    ================================================================================
    """
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


# ===============================================================================
# HyDE 假设文档生成
# ===============================================================================
def generate_hypothetical_document(query: str) -> str:
    """
    ================================================================================
    [辅助函数] generate_hypothetical_document - HyDE 查询扩展
    ================================================================================
    功能: 让 LLM 先生成一个假设性的回答，再用它进行检索
    
    原理: HyDE (Hypothetical Document Embeddings)
        - 假设性回答可能与真实文档有更好的语义相似度
        - 用假设回答检索可以召回更多相关文档
    
    示例:
        输入: "什么是机器学习？"
        输出: "机器学习是人工智能的一个分支，它使计算机能够从数据中学习..."
    
    实现: 调用 LLM 生成假设性回答
    ================================================================================
    """
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


import requests
from langchain.chat_models import init_chat_model
