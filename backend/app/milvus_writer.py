from app.utils.embedding_service import embedding_service
from app.utils.milvus_service import milvus_service
from app.utils.document_loader import document_loader
from app.utils.parent_chunk_store import parent_chunk_store
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

        self._save_parent_chunks(docs)
        
        texts = [doc["text"] for doc in docs]
        dense_embeddings = self.embedding_service.get_embeddings(texts)
        sparse_embeddings = self.embedding_service.get_sparse_embeddings(texts)
        
        data = []
        for i, doc in enumerate(docs):
            data.append({
                "text": doc["text"][:2000],
                "filename": doc["filename"],
                "file_type": doc["file_type"],
                "page_number": doc.get("page_number", 0),
                "chunk_id": doc.get("chunk_id", ""),
                "parent_chunk_id": doc.get("parent_chunk_id", ""),
                "chunk_level": doc.get("chunk_level", 3),
                "dense_embedding": dense_embeddings[i] if i < len(dense_embeddings) else [],
                "sparse_embedding": sparse_embeddings[i] if i < len(sparse_embeddings) else {},
            })
        
        self.milvus_service.insert(data)
        return len(docs)

    @staticmethod
    def _save_parent_chunks(docs: list[dict]) -> None:
        parent_payload: dict[str, dict] = {}
        for doc in docs:
            parent_id = (doc.get("parent_chunk_id") or "").strip()
            parent_text = (doc.get("parent_text") or "").strip()
            if not parent_id or not parent_text:
                continue
            if parent_id in parent_payload:
                continue
            parent_payload[parent_id] = {
                "text": parent_text,
                "metadata": {
                    "filename": doc.get("filename", ""),
                    "file_type": doc.get("file_type", ""),
                    "file_path": doc.get("file_path", ""),
                    "page_number": doc.get("page_number", 0),
                    "parent_chunk_id": "",
                    "root_chunk_id": parent_id,
                    "chunk_level": 1,
                    "chunk_idx": 0,
                },
            }

        for parent_id, payload in parent_payload.items():
            try:
                parent_chunk_store.save_chunk(parent_id, payload["text"], payload["metadata"])
            except Exception as exc:
                logger.warning("save_parent_chunk_failed chunk_id=%s err=%s", parent_id, exc)


milvus_writer = MilvusWriter()
