'''
@create_time: 2026/3/30
@Author: GeChao
@File: document_loader.py
'''
import os
from typing import Dict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader


class DocumentLoader:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            separators=["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""],
        )

    @staticmethod
    def _build_chunk_id(filename: str, page_number: int, index: int) -> str:
        return f"{filename}::p{page_number}::{index}"

    def load_document(self, file_path: str, filename: str) -> list[dict]:
        file_lower = filename.lower()
        
        if file_lower.endswith(".pdf"):
            doc_type = "PDF"
            loader = PyPDFLoader(file_path)
        elif file_lower.endswith((".docx", ".doc")):
            doc_type = "Word"
            loader = Docx2txtLoader(file_path)
        elif file_lower.endswith((".xlsx", ".xls")):
            doc_type = "Excel"
            loader = UnstructuredExcelLoader(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {filename}")

        try:
            raw_docs = loader.load()
            documents = []
            for idx, doc in enumerate(raw_docs):
                texts = self._splitter.split_text(doc.page_content or "")
                for chunk_idx, text in enumerate(texts):
                    if not text.strip():
                        continue
                    documents.append({
                        "text": text.strip(),
                        "filename": filename,
                        "file_path": file_path,
                        "file_type": doc_type,
                        "page_number": doc.metadata.get("page", idx),
                        "chunk_id": self._build_chunk_id(filename, doc.metadata.get("page", 0), chunk_idx),
                        "chunk_level": 3,
                    })
            return documents
        except Exception as e:
            raise Exception(f"处理文档失败: {str(e)}")


document_loader = DocumentLoader()
