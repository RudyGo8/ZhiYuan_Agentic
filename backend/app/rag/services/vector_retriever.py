'''
@create_time: 2026/4/27 下午4:00
@Author: GeChao
@File: vector_retriever.py
'''
from app.utils.embedding_service import embedding_service
from app.utils.milvus_service import milvus_service


def vector_retrieve(query: str, top_k: int = 5) -> tuple[list[dict], dict]:

    milvus_service.init_collection()
    dense_embedding = embedding_service.get_embedding(query)
    sparse_embedding = embedding_service.get_sparse_embedding(query)

    # 混合检索
    retrieval_mode = "hybrid"
    try:
        docs = milvus_service.hybrid_search(dense_embedding, sparse_embedding, top_k * 2)
    except Exception:
        retrieval_mode = "dense"
        docs = milvus_service.dense_search(dense_embedding, top_k * 2)
    meta = {
        "retrieval_mode": retrieval_mode,
        "candidate_k": len(docs),
    }

    return docs, meta


