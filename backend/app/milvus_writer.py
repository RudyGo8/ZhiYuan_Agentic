from app.utils.embedding_service import embedding_service
from app.utils.milvus_service import milvus_service
from app.utils.document_loader import document_loader
from app.config import logger


class MilvusWriter:
    def __init__(self):
        self.embedding_service = embedding_service
        self.milvus_service = milvus_service
        self.document_loader = document_loader

    def write_documents(self, file_path: str, filename: str) -> int:
        self.milvus_service.init_collection()
        
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


milvus_writer = MilvusWriter()
