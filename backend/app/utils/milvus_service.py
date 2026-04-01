'''
@create_time: 2026/3/30
@Author: GeChao
@File: milvus_service.py
'''
from pymilvus import MilvusClient, DataType, AnnSearchRequest, RRFRanker
from app.config import MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION


class MilvusService:
    def __init__(self):
        self.host = MILVUS_HOST
        self.port = MILVUS_PORT
        self.collection_name = MILVUS_COLLECTION
        self.uri = f"http://{self.host}:{self.port}"
        self.client = None

    def _get_client(self):
        if self.client is None:
            self.client = MilvusClient(uri=self.uri)
        return self.client

    def init_collection(self, dense_dim: int = 1536, force_recreate: bool = False):
        client = self._get_client()
        
        if force_recreate or not client.has_collection(self.collection_name):
            if client.has_collection(self.collection_name):
                try:
                    client.drop_collection(self.collection_name)
                except:
                    pass
            
            schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
            schema.add_field("dense_embedding", DataType.FLOAT_VECTOR, dim=dense_dim)
            schema.add_field("sparse_embedding", DataType.SPARSE_FLOAT_VECTOR)
            schema.add_field("text", DataType.VARCHAR, max_length=2000)
            schema.add_field("filename", DataType.VARCHAR, max_length=255)
            schema.add_field("file_type", DataType.VARCHAR, max_length=50)
            schema.add_field("chunk_id", DataType.VARCHAR, max_length=512)
            schema.add_field("parent_chunk_id", DataType.VARCHAR, max_length=512)
            schema.add_field("chunk_level", DataType.INT64)

            index_params = client.prepare_index_params()
            index_params.add_index(field_name="dense_embedding", index_type="HNSW", metric_type="IP", params={"M": 16, "efConstruction": 256})
            index_params.add_index(field_name="sparse_embedding", index_type="SPARSE_INVERTED_INDEX", metric_type="IP", params={"drop_ratio_build": 0.2})

            client.create_collection(collection_name=self.collection_name, schema=schema, index_params=index_params)
        
        try:
            client.load_collection(self.collection_name)
        except Exception:
            pass

    def insert(self, data: list[dict]):
        return self._get_client().insert(self.collection_name, data)

    def query(self, filter_expr: str = "", output_fields: list = None, limit: int = 100):
        return self._get_client().query(
            collection_name=self.collection_name,
            filter=filter_expr,
            output_fields=output_fields or ["filename", "file_type", "text", "chunk_id"],
            limit=limit
        )

    def delete(self, filter_expr: str):
        return self._get_client().delete(collection_name=self.collection_name, filter=filter_expr)

    def hybrid_search(self, dense_embedding: list[float], sparse_embedding: dict, top_k: int = 5) -> list[dict]:
        output_fields = ["text", "filename", "file_type", "chunk_id", "parent_chunk_id", "chunk_level"]
        
        dense_search = AnnSearchRequest(
            data=[dense_embedding],
            anns_field="dense_embedding",
            param={"metric_type": "IP", "params": {"ef": 64}},
            limit=top_k * 2,
        )
        sparse_search = AnnSearchRequest(
            data=[sparse_embedding],
            anns_field="sparse_embedding",
            param={"metric_type": "IP", "params": {"drop_ratio_search": 0.2}},
            limit=top_k * 2,
        )
        
        reranker = RRFRanker(k=60)
        
        try:
            results = self._get_client().hybrid_search(
                collection_name=self.collection_name,
                reqs=[dense_search, sparse_search],
                ranker=reranker,
                limit=top_k,
                output_fields=output_fields
            )
            
            formatted = []
            for hits in results:
                for hit in hits:
                    formatted.append({
                        "text": hit.get("text", ""),
                        "filename": hit.get("filename", ""),
                        "file_type": hit.get("file_type", ""),
                        "chunk_id": hit.get("chunk_id", ""),
                        "score": hit.get("distance", 0.0)
                    })
            return formatted
        except Exception:
            return self.dense_search(dense_embedding, top_k)

    def dense_search(self, dense_embedding: list[float], top_k: int = 5) -> list[dict]:
        results = self._get_client().search(
            collection_name=self.collection_name,
            data=[dense_embedding],
            anns_field="dense_embedding",
            search_params={"metric_type": "IP", "params": {"ef": 64}},
            limit=top_k,
            output_fields=["text", "filename", "file_type", "chunk_id", "parent_chunk_id", "chunk_level"],
        )
        
        formatted = []
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {}) if isinstance(hit, dict) else hit
                if hasattr(hit, 'entity'):
                    entity = hit.entity
                text = entity.get("text", "") if isinstance(entity, dict) else ""
                filename = entity.get("filename", "") if isinstance(entity, dict) else ""
                file_type = entity.get("file_type", "") if isinstance(entity, dict) else ""
                chunk_id = entity.get("chunk_id", "") if isinstance(entity, dict) else ""
                score = hit.get("distance", 0.0) if isinstance(hit, dict) else getattr(hit, 'distance', 0.0)
                formatted.append({
                    "text": text,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_id": chunk_id,
                    "score": score
                })
        return formatted


milvus_service = MilvusService()
