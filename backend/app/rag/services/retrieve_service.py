'''
@create_time: 2026/4/27 下午4:01
@Author: GeChao
@File: retrieve_service.py
'''
from app.rag.services.vector_retriever import vector_retrieve
from app.rag.services.reranker import rerank_documents
from app.rag.services.merger import auto_merge_chunks
from app.utils.doc_normalizer import normalize_docs


def retrieve_documents(query: str, top_k: int = 5) -> dict:
    candidate_k = top_k * 2
    docs, retrieve_meta = vector_retrieve(query, candidate_k)
    docs = normalize_docs(docs)
    docs, rerank_meta = rerank_documents(query, docs)
    docs = normalize_docs(docs)
    docs, merge_meta = auto_merge_chunks(docs, top_k)
    docs = normalize_docs(docs)

    # d: str , -> dict
    for index, doc in enumerate(docs):
        doc["final_rank"] = index + 1

    meta = {}
    meta.update(retrieve_meta)
    meta.update(merge_meta)
    meta.update(rerank_meta)

    meta["final_k"] = len(docs)

    return {
        "docs": docs[:top_k],
        "meta": meta,
    }
