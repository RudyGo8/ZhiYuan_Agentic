'''
@create_time: 2026/3/30
@Author: GeChao
@File: rag_service.py
'''
from app.utils.embedding_service import embedding_service
from app.utils.milvus_service import milvus_service
from app.utils.document_loader import document_loader
from app.config import logger


class RagService:
    def __init__(self):
        self.embedding_service = embedding_service
        self.milvus_service = milvus_service
        self.document_loader = document_loader

    def init_milvus(self):
        self.milvus_service.init_collection()

    def upload_document(self, file_path: str, filename: str) -> int:
        self.init_milvus()
        
        docs = self.document_loader.load_document(file_path, filename)
        if not docs:
            return 0
        
        texts = [doc["text"] for doc in docs]
        dense_embeddings = self.embedding_service.get_embeddings(texts)
        sparse_embeddings = self.embedding_service.get_sparse_embeddings(texts)
        
        data = []
        for i, doc in enumerate(docs):
            data.append({
                "text": doc["text"][:2000],
                "filename": doc["filename"],
                "file_type": doc["file_type"],
                "chunk_id": doc.get("chunk_id", ""),
                "parent_chunk_id": doc.get("parent_chunk_id", ""),
                "chunk_level": doc.get("chunk_level", 3),
                "dense_embedding": dense_embeddings[i] if i < len(dense_embeddings) else [],
                "sparse_embedding": sparse_embeddings[i] if i < len(sparse_embeddings) else {},
            })
        
        self.milvus_service.insert(data)
        return len(docs)

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        try:
            self.init_milvus()
            dense_embedding = self.embedding_service.get_embedding(query)
            sparse_embedding = self.embedding_service.get_sparse_embedding(query)
            results = self.milvus_service.hybrid_search(dense_embedding, sparse_embedding, top_k)
            return results
        except Exception as e:
            logger.error(f"RAG检索失败: {str(e)}")
            try:
                dense_embedding = self.embedding_service.get_embedding(query)
                return self.milvus_service.dense_search(dense_embedding, top_k)
            except Exception as e2:
                logger.error(f"降级检索也失败: {str(e2)}")
                return []

    def format_context(self, docs: list[dict]) -> str:
        if not docs:
            return ""
        chunks = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("filename", "Unknown")
            text = doc.get("text", "")
            chunks.append(f"[{i}] {source}:\n{text}")
        return "\n\n".join(chunks)


rag_service = RagService()
