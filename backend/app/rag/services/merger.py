'''
@create_time: 2026/4/27 下午4:00
@Author: GeChao
@File: merger.py
'''

from app.config import (
    AUTO_MERGE_ENABLED,
    AUTO_MERGE_THRESHOLD,
    LEAF_RETRIEVE_LEVEL
)


def _parse_bool(value) -> bool:
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


# 配置参数解析
AUTO_MERGE_ENABLED_VALUE = _parse_bool(AUTO_MERGE_ENABLED)
AUTO_MERGE_THRESHOLD = int(AUTO_MERGE_THRESHOLD) if AUTO_MERGE_THRESHOLD else 2
LEAF_RETRIEVE_LEVEL = int(LEAF_RETRIEVE_LEVEL) if LEAF_RETRIEVE_LEVEL else 3


def auto_merge_chunks(results: list[dict], top_k: int = 5):
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
        "leaf_retrieve_level": LEAF_RETRIEVE_LEVEL,
        "auto_merge_enabled": auto_merge_enabled,
        "auto_merge_applied": auto_merge_applied,
        "auto_merge_threshold": AUTO_MERGE_THRESHOLD,
        "auto_merge_replaced_chunks": auto_merge_replaced_chunks,
        "auto_merge_steps": auto_merge_steps,
    }

    return results[:top_k], meta
