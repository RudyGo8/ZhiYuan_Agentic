from sqlalchemy import Column, Integer, String, Text, JSON
from app.database import Base
from app.cache import cache


class ParentChunkStore:
    """父级分块存储"""
    
    def _cache_key(self, chunk_id: str) -> str:
        return f"parent_chunk:{chunk_id}"
    
    def get_chunk(self, chunk_id: str) -> dict | None:
        cached = cache.get_json(self._cache_key(chunk_id))
        if cached is not None:
            return cached
        
        from app.models.db_parent_chunk import ParentChunk
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            row = db.query(ParentChunk).filter(ParentChunk.chunk_id == chunk_id).first()
            if row:
                result = {
                    "chunk_id": row.chunk_id,
                    "text": row.text,
                    "metadata": row.metadata_json or {}
                }
                cache.set_json(self._cache_key(chunk_id), result)
                return result
            return None
        finally:
            db.close()
    
    def save_chunk(self, chunk_id: str, text: str, metadata: dict = None):
        from app.models.db_parent_chunk import ParentChunk
        from app.database import SessionLocal

        metadata = metadata or {}
        filename = (metadata.get("filename") or "").strip() or "unknown"
        file_type = (metadata.get("file_type") or "").strip()
        file_path = (metadata.get("file_path") or "").strip()
        page_number = int(metadata.get("page_number") or 0)
        parent_chunk_id = (metadata.get("parent_chunk_id") or "").strip()
        root_chunk_id = (metadata.get("root_chunk_id") or "").strip()
        chunk_level = int(metadata.get("chunk_level") or 0)
        chunk_idx = int(metadata.get("chunk_idx") or 0)

        db = SessionLocal()
        try:
            existing = db.query(ParentChunk).filter(ParentChunk.chunk_id == chunk_id).first()
            if existing:
                existing.text = text
                existing.filename = filename
                existing.file_type = file_type
                existing.file_path = file_path
                existing.page_number = page_number
                existing.parent_chunk_id = parent_chunk_id
                existing.root_chunk_id = root_chunk_id
                existing.chunk_level = chunk_level
                existing.chunk_idx = chunk_idx
                existing.metadata_json = metadata
            else:
                chunk = ParentChunk(
                    chunk_id=chunk_id,
                    text=text,
                    filename=filename,
                    file_type=file_type,
                    file_path=file_path,
                    page_number=page_number,
                    parent_chunk_id=parent_chunk_id,
                    root_chunk_id=root_chunk_id,
                    chunk_level=chunk_level,
                    chunk_idx=chunk_idx,
                    metadata_json=metadata,
                )
                db.add(chunk)
            db.commit()
            cache.delete(self._cache_key(chunk_id))
        finally:
            db.close()
    
    def delete_chunk(self, chunk_id: str):
        from app.models.db_parent_chunk import ParentChunk
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            db.query(ParentChunk).filter(ParentChunk.chunk_id == chunk_id).delete()
            db.commit()
            cache.delete(self._cache_key(chunk_id))
        finally:
            db.close()


parent_chunk_store = ParentChunkStore()
