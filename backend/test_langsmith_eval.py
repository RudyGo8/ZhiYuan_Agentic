from typing import Any, Optional
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv

# # 必须在导入 app 模块之前加载环境变量
# load_dotenv()
#
# from langsmith import evaluate
#
# # 添加 app 目录到路径
# app_path = os.path.join(os.path.dirname(__file__), "app")
# if app_path not in sys.path:
#     sys.path.insert(0, app_path)
#
# from app.agent import chat_with_agent
#
#
# def _extract_answer(outputs: Any) -> str:
#     if isinstance(outputs, dict):
#         # 优先取真实最终回复字段
#         answer = outputs.get("response") or outputs.get("answer") or outputs.get("output")
#         return str(answer or "").strip()
#     if hasattr(outputs, "outputs") and isinstance(outputs.outputs, dict):
#         answer = (
#                 outputs.outputs.get("response")
#                 or outputs.outputs.get("answer")
#                 or outputs.outputs.get("output")
#         )
#         return str(answer or "").strip()
#     return ""
#
#
# def _extract_reference(reference_outputs: Optional[dict]) -> str:
#     if not isinstance(reference_outputs, dict):
#         return ""
#     for key in ("response", "answer", "output", "expected_answer"):
#         value = reference_outputs.get(key)
#         if value:
#             return str(value).strip()
#     return ""
#
#
# # 1. Select your dataset
# dataset_name = "Agentic_Rag_test1"
#
#
# # 2. Define an evaluator (评估最终答案，不评估检索块)
# def custom_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
#     answer = _extract_answer(run_outputs)
#     if not answer:
#         return {"score": 0, "key": "answer_quality"}
#     if "Retrieved Chunks:" in answer:
#         return {"score": 0, "key": "answer_quality"}
#
#     reference = _extract_reference(reference_outputs)
#     if not reference:
#         return {"score": 1, "key": "answer_quality"}
#
#     # 有参考答案时，至少保证存在一定语义重合（使用字符集合重合率做轻量检查）
#     answer_chars = {ch for ch in answer if not ch.isspace()}
#     ref_chars = {ch for ch in reference if not ch.isspace()}
#     if not answer_chars or not ref_chars:
#         return {"score": 0, "key": "answer_quality"}
#
#     overlap = len(answer_chars & ref_chars) / max(1, len(ref_chars))
#     return {"score": 1 if overlap >= 0.2 else 0, "key": "answer_quality"}
#
#
# # 直接调用你现有的完整 Agent 流程作为评估对象
# def target_function(inputs: dict) -> dict:
#     question = inputs["question"]
#     # 每条评估样本使用独立会话，避免上下文串扰
#     session_id = f"langsmith_eval_{uuid4().hex}"
#     result = chat_with_agent(
#         user_text=question,
#         user_id="langsmith_eval_user",
#         session_id=session_id,
#     )
#
#     response_text = ""
#     rag_trace = {}
#     if isinstance(result, dict):
#         response_text = str(result.get("response", "") or "")
#         rag_trace = result.get("rag_trace", {}) or {}
#     else:
#         response_text = str(result)
#
#     return {
#         "response": response_text,
#         "rag_trace": rag_trace,
#     }
#
#
# # 3. Run an evaluation
# # For more info on evaluators, see: https://docs.langchain.com/langsmith/evaluation-concepts
# evaluate(
#     target_function,
#     data=dataset_name,
#     evaluators=[custom_evaluator],
#     experiment_prefix="Agentic_Rag_test1 experiment",
#     max_concurrency=1,
# )

from __future__ import annotations

from typing import Any, Optional
import json
import math
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv
from langsmith import evaluate

# 必须在导入 app 模块之前加载环境变量
load_dotenv()

# 添加 app 目录到路径
app_path = os.path.join(os.path.dirname(__file__), "app")
if app_path not in sys.path:
  sys.path.insert(0, app_path)

from app.agent import chat_with_agent


DATASET_NAME = os.getenv("LANGSMITH_DATASET", "Agentic_Rag_test1")
EXPERIMENT_PREFIX = os.getenv("LANGSMITH_EXPERIMENT_PREFIX", f"{DATASET_NAME} experiment")
MAX_CONCURRENCY = int(os.getenv("LANGSMITH_MAX_CONCURRENCY", "1"))
RETRIEVAL_K = int(os.getenv("RAG_EVAL_TOP_K", "5"))


def _extract_answer(outputs: Any) -> str:
  if isinstance(outputs, dict):
      answer = outputs.get("response") or outputs.get("answer") or outputs.get("output")
      return str(answer or "").strip()
  if hasattr(outputs, "outputs") and isinstance(outputs.outputs, dict):
      answer = outputs.outputs.get("response") or outputs.outputs.get("answer") or outputs.outputs.get("output")
      return str(answer or "").strip()
  return ""


def _extract_rag_trace(outputs: Any) -> dict:
  if isinstance(outputs, dict):
      trace = outputs.get("rag_trace")
      return trace if isinstance(trace, dict) else {}
  if hasattr(outputs, "outputs") and isinstance(outputs.outputs, dict):
      trace = outputs.outputs.get("rag_trace")
      return trace if isinstance(trace, dict) else {}
  return {}


def _extract_reference_answer(reference_outputs: Optional[dict]) -> str:
  if not isinstance(reference_outputs, dict):
      return ""
  for key in ("response", "answer", "output", "expected_answer"):
      value = reference_outputs.get(key)
      if value:
          return str(value).strip()
  return ""


def _to_list(value: Any) -> list[str]:
  if value is None:
      return []
  if isinstance(value, (list, tuple, set)):
      return [str(v).strip() for v in value if str(v).strip()]
  if isinstance(value, str):
      raw = value.strip()
      if not raw:
          return []
      if raw.startswith("[") and raw.endswith("]"):
          try:
              parsed = json.loads(raw)
              if isinstance(parsed, list):
                  return [str(v).strip() for v in parsed if str(v).strip()]
          except Exception:
              pass
      normalized = raw.replace("\n", ",").replace(";", ",")
      return [part.strip() for part in normalized.split(",") if part.strip()]
  return [str(value).strip()] if str(value).strip() else []


def _extract_expected_doc_ids(reference_outputs: Optional[dict]) -> set[str]:
  if not isinstance(reference_outputs, dict):
      return set()
  for key in ("expected_doc_ids", "expected_chunk_ids", "relevant_doc_ids", "gold_doc_ids"):
      values = _to_list(reference_outputs.get(key))
      if values:
          return set(values)
  return set()


def _extract_expected_filenames(reference_outputs: Optional[dict]) -> set[str]:
  if not isinstance(reference_outputs, dict):
      return set()
  for key in ("expected_filenames", "relevant_filenames", "gold_filenames", "expected_sources"):
      values = _to_list(reference_outputs.get(key))
      if values:
          return set(values)
  return set()


def _extract_retrieved_chunks(outputs: Any) -> list[dict]:
  rag_trace = _extract_rag_trace(outputs)
  chunks = rag_trace.get("retrieved_chunks", [])
  return chunks if isinstance(chunks, list) else []


def _chunk_doc_id(chunk: dict) -> str:
  if not isinstance(chunk, dict):
      return ""
  chunk_id = str(chunk.get("chunk_id") or "").strip()
  if chunk_id:
      return chunk_id
  filename = str(chunk.get("filename") or "").strip()
  page = str(chunk.get("page_number") if chunk.get("page_number") is not None else "").strip()
  if filename and page:
      return f"{filename}::p{page}"
  return filename


def _chunk_filename(chunk: dict) -> str:
  if not isinstance(chunk, dict):
      return ""
  return str(chunk.get("filename") or "").strip()


def _build_relevance_vector(outputs: Any, reference_outputs: Optional[dict], k: int) -> tuple[list[int], int]:
  expected_ids = _extract_expected_doc_ids(reference_outputs)
  expected_filenames = _extract_expected_filenames(reference_outputs)
  expected_total = len(expected_ids | expected_filenames)
  chunks = _extract_retrieved_chunks(outputs)[:k]

  relevance: list[int] = []
  for chunk in chunks:
      doc_id = _chunk_doc_id(chunk)
      filename = _chunk_filename(chunk)
      is_relevant = (doc_id in expected_ids) or (filename in expected_filenames)
      relevance.append(1 if is_relevant else 0)
  return relevance, expected_total


def _answer_quality_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  answer = _extract_answer(run_outputs)
  if not answer:
      return {"score": 0.0, "key": "answer_quality", "comment": "empty_answer"}
  if "Retrieved Chunks:" in answer:
      return {"score": 0.0, "key": "answer_quality", "comment": "raw_tool_output"}

  reference = _extract_reference_answer(reference_outputs)
  if not reference:
      return {"score": 1.0, "key": "answer_quality", "comment": "no_reference_answer"}

  answer_chars = {ch for ch in answer if not ch.isspace()}
  ref_chars = {ch for ch in reference if not ch.isspace()}
  if not answer_chars or not ref_chars:
      return {"score": 0.0, "key": "answer_quality", "comment": "empty_after_normalize"}

  overlap = len(answer_chars & ref_chars) / max(1, len(ref_chars))
  return {"score": 1.0 if overlap >= 0.2 else 0.0, "key": "answer_quality"}


def _retrieval_label_coverage_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  expected_ids = _extract_expected_doc_ids(reference_outputs)
  expected_filenames = _extract_expected_filenames(reference_outputs)
  has_labels = bool(expected_ids or expected_filenames)
  return {
      "score": 1.0 if has_labels else 0.0,
      "key": f"retrieval_labels_available_at_{RETRIEVAL_K}",
      "comment": "expected_doc_ids/expected_filenames",
  }


def _retrieval_hit_at_k_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  relevance, expected_total = _build_relevance_vector(run_outputs, reference_outputs, RETRIEVAL_K)
  if expected_total == 0:
      return {"score": 0.0, "key": f"retrieval_hit_at_{RETRIEVAL_K}", "comment": "missing_retrieval_labels"}
  return {"score": 1.0 if any(relevance) else 0.0, "key": f"retrieval_hit_at_{RETRIEVAL_K}"}


def _retrieval_recall_at_k_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  relevance, expected_total = _build_relevance_vector(run_outputs, reference_outputs, RETRIEVAL_K)
  if expected_total == 0:
      return {"score": 0.0, "key": f"retrieval_recall_at_{RETRIEVAL_K}", "comment": "missing_retrieval_labels"}
  hits = int(sum(relevance))
  recall = hits / max(1, expected_total)
  return {"score": float(recall), "key": f"retrieval_recall_at_{RETRIEVAL_K}"}


def _retrieval_mrr_at_k_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  relevance, expected_total = _build_relevance_vector(run_outputs, reference_outputs, RETRIEVAL_K)
  if expected_total == 0:
      return {"score": 0.0, "key": f"retrieval_mrr_at_{RETRIEVAL_K}", "comment": "missing_retrieval_labels"}
  for idx, rel in enumerate(relevance, start=1):
      if rel == 1:
          return {"score": 1.0 / idx, "key": f"retrieval_mrr_at_{RETRIEVAL_K}"}
  return {"score": 0.0, "key": f"retrieval_mrr_at_{RETRIEVAL_K}"}


def _retrieval_ndcg_at_k_evaluator(run_outputs: dict, reference_outputs: dict) -> dict:
  relevance, expected_total = _build_relevance_vector(run_outputs, reference_outputs, RETRIEVAL_K)
  if expected_total == 0:
      return {"score": 0.0, "key": f"retrieval_ndcg_at_{RETRIEVAL_K}", "comment": "missing_retrieval_labels"}
  if not relevance:
      return {"score": 0.0, "key": f"retrieval_ndcg_at_{RETRIEVAL_K}"}

  dcg = 0.0
  for idx, rel in enumerate(relevance, start=1):
      if rel:
          dcg += 1.0 / math.log2(idx + 1)

  ideal_relevant = min(expected_total, RETRIEVAL_K)
  if ideal_relevant <= 0:
      return {"score": 0.0, "key": f"retrieval_ndcg_at_{RETRIEVAL_K}"}

  idcg = 0.0
  for idx in range(1, ideal_relevant + 1):
      idcg += 1.0 / math.log2(idx + 1)

  ndcg = dcg / idcg if idcg > 0 else 0.0
  return {"score": float(ndcg), "key": f"retrieval_ndcg_at_{RETRIEVAL_K}"}


def target_function(inputs: dict) -> dict:
  question = inputs["question"]
  session_id = f"langsmith_eval_{uuid4().hex}"
  result = chat_with_agent(
      user_text=question,
      user_id="langsmith_eval_user",
      session_id=session_id,
  )

  response_text = ""
  rag_trace = {}
  if isinstance(result, dict):
      response_text = str(result.get("response", "") or "")
      rag_trace = result.get("rag_trace", {}) or {}
  else:
      response_text = str(result)

  return {
      "response": response_text,
      "rag_trace": rag_trace,
  }


evaluate(
  target_function,
  data=DATASET_NAME,
  evaluators=[
      _answer_quality_evaluator,
      _retrieval_label_coverage_evaluator,
      _retrieval_hit_at_k_evaluator,
      _retrieval_recall_at_k_evaluator,
      _retrieval_mrr_at_k_evaluator,
      _retrieval_ndcg_at_k_evaluator,
  ],
  experiment_prefix=EXPERIMENT_PREFIX,
  max_concurrency=MAX_CONCURRENCY,
)
