'''
@create_time: 2025/09/03
@Author: GeChao
@File: config.py
'''
import json
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3307"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "langchain_app")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "rag_agent")
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "300"))

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "rag_embeddings")

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
MODEL = os.getenv("MODEL", "qwen-plus")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDER = os.getenv("EMBEDDER", "text-embedding-v2")
GRADE_MODEL = os.getenv("GRADE_MODEL", "qwen-plus")

AUTO_MERGE_ENABLED = os.getenv("AUTO_MERGE_ENABLED", "true")
AUTO_MERGE_THRESHOLD = os.getenv("AUTO_MERGE_THRESHOLD", "2")
LEAF_RETRIEVE_LEVEL = os.getenv("LEAF_RETRIEVE_LEVEL", "3")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "")
PASSWORD_PBKDF2_ROUNDS = int(os.getenv("PASSWORD_PBKDF2_ROUNDS", "310000"))

MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"
MCP_SERVERS_JSON = os.getenv("MCP_SERVERS_JSON", "")
MCP_TOOL_TIMEOUT_SECONDS = float(os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "12"))

LOG_PATH = os.getenv("LOG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"))


def json_formatter(record):
    log_record = {
        "time": record.asctime,
        "name": record.name,
        "level": record.levelname,
        "message": record.getMessage(),
        "filename": record.filename,
        "funcName": record.funcName,
        "lineno": record.lineno
    }
    return json.dumps(log_record, ensure_ascii=False)


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        record.asctime = self.formatTime(record)
        return json_formatter(record)


def setup_logging(log_file_path=None):
    root_logger = logging.getLogger()
    if getattr(root_logger, "_rag_agent_logging_configured", False):
        return

    if log_file_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = "%s/rag_agent_%s.log" % (LOG_PATH, timestamp)

    root_logger.setLevel(logging.INFO)
    fmt = JsonLogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)
    root_logger.addHandler(stream_handler)

    try:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = TimedRotatingFileHandler(log_file_path, when='midnight', interval=1, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(fmt)
        root_logger.addHandler(file_handler)
    except OSError as e:
        root_logger.warning("File logging disabled, fallback to stdout only: %s", e)

    root_logger._rag_agent_logging_configured = True

setup_logging()
logger = logging.getLogger(__name__)
