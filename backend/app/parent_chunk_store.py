from sqlalchemy import Column, Integer, String, Text, JSON
from app.database import Base
from app.cache import cache


class ParentChunkStore:
    """父级分块存储（PostgreSQL + Redis 缓存）。"""
    
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
        
        db = SessionLocal()
        try:
            existing = db.query(ParentChunk).filter(ParentChunk.chunk_id == chunk_id).first()
            if existing:
                existing.text = text
                existing.metadata_json = metadata or {}
            else:
                chunk = ParentChunk(chunk_id=chunk_id, text=text, metadata_json=metadata or {})
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
