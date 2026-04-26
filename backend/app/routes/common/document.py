'''
@create_time: 2026/01/23
@Author: GeChao
@File: document.py
'''
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models.db_user import User
from app.schemas.auth import (
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.utils.auth_utils import require_admin
from app.utils.milvus_service import milvus_service

router_r1 = APIRouter(
    prefix="/api/r1/documents",
    tags=["documents"]
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "documents"


def _sanitize_filename(raw_name: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    safe_name = Path(name).name.strip()
    if safe_name != name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="非法文件名")
    return safe_name


def _escape_milvus_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@router_r1.get("", response_model=DocumentListResponse)
async def list_documents(_: User = Depends(require_admin)):
    try:
        milvus_service.init_collection()
        results = milvus_service.query(output_fields=["filename", "file_type"], limit=10000)

        file_stats = {}
        for item in results:
            filename = item.get("filename", "")
            file_type = item.get("file_type", "")
            if filename not in file_stats:
                file_stats[filename] = {"filename": filename, "file_type": file_type, "chunk_count": 0}
            file_stats[filename]["chunk_count"] += 1

        documents = [DocumentInfo(**stats) for stats in file_stats.values()]
        return DocumentListResponse(documents=documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


# 上传文档 - 保存磁盘 - 切块向量化写入Milvus - 返回分块数量
@router_r1.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), _: User = Depends(require_admin)):
    filename = _sanitize_filename(file.filename or "")
    file_lower = filename.lower()

    if not (
            file_lower.endswith(".pdf")
            or file_lower.endswith((".docx", ".doc"))
            or file_lower.endswith((".xlsx", ".xls"))
    ):
        raise HTTPException(status_code=400, detail="仅支持 PDF、Word 和 Excel 文档")

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        from app.milvus_writer import milvus_writer
        chunk_count = milvus_writer.write_documents(str(file_path), filename)

        return DocumentUploadResponse(
            filename=filename,
            chunks_processed=chunk_count,
            message=f"成功上传并处理 {filename}，共 {chunk_count} 个分块",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router_r1.delete("/{filename}", response_model=DocumentDeleteResponse)
async def delete_document(filename: str, _: User = Depends(require_admin)):
    try:
        safe_filename = _sanitize_filename(filename)
        milvus_service.init_collection()
        delete_expr = f'filename == "{_escape_milvus_string(safe_filename)}"'
        result = milvus_service.delete(delete_expr)

        return DocumentDeleteResponse(
            filename=safe_filename,
            chunks_deleted=result.get("delete_count", 0) if isinstance(result, dict) else 0,
            message=f"成功删除文档 {safe_filename} 的向量数据",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")
