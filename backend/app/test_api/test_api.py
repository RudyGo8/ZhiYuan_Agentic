# -*- coding: utf-8 -*-
"""
RAG Agent API Tests
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"
TEST_USER = "test1"
TEST_PASS = "123456"


class APITester:
    def __init__(self):
        self.token = None
        self.session_id = None

    def _headers(self, token=None):
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def test_01_register(self):
        print("\n=== Test 1: Register ===")
        resp = requests.post(f"{BASE_URL}/api/r1/auth/register", json={
            "username": TEST_USER, "password": TEST_PASS
        })
        print(f"Status: {resp.status_code}")
        return resp.status_code in [200, 201, 400, 409]

    def test_02_login(self):
        print("\n=== Test 2: Login ===")
        resp = requests.post(f"{BASE_URL}/api/r1/auth/login", json={
            "username": TEST_USER, "password": TEST_PASS
        })
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
        return resp.status_code == 200

    def test_03_get_me(self):
        print("\n=== Test 3: Get Me ===")
        if not self.token:
            self.test_02_login()
        resp = requests.get(f"{BASE_URL}/api/r1/auth/me", headers=self._headers(self.token))
        print(f"Status: {resp.status_code}")
        return resp.status_code == 200

    def test_04_chat(self):
        print("\n=== Test 4: Chat ===")
        if not self.token:
            self.test_02_login()
        session_id = f"session_{int(time.time())}"
        resp = requests.post(f"{BASE_URL}/api/r1/chat", headers=self._headers(self.token),
                            json={"message": "Hi", "session_id": session_id})
        print(f"Status: {resp.status_code}")
        return resp.status_code == 200

    def test_05_stream(self):
        print("\n=== Test 5: Stream Chat ===")
        if not self.token:
            self.test_02_login()
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/api/r1/chat/stream",
            data=json.dumps({"message": "Hi", "session_id": "test"}).encode('utf-8'),
            headers=self._headers(self.token), method='POST'
        )
        req.add_header('Accept', 'text/event-stream')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"Status: {r.status}")
                return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def test_06_sessions(self):
        print("\n=== Test 6: Sessions ===")
        if not self.token:
            self.test_02_login()
        resp = requests.get(f"{BASE_URL}/api/r1/chat/sessions", headers=self._headers(self.token))
        print(f"Status: {resp.status_code}")
        return resp.status_code == 200

    def test_07_get_session(self):
        print("\n=== Test 7: Get Session ===")
        if not self.token:
            self.test_02_login()
        s = f"session_test_{int(time.time())}"
        requests.post(f"{BASE_URL}/api/r1/chat", headers=self._headers(self.token),
                     json={"message": "test", "session_id": s})
        resp = requests.get(f"{BASE_URL}/api/r1/chat/sessions/{s}", headers=self._headers(self.token))
        print(f"Status: {resp.status_code}")
        return resp.status_code == 200

    def test_08_delete_session(self):
        print("\n=== Test 8: Delete Session ===")
        if not self.token:
            self.test_02_login()
        s = f"session_del_{int(time.time())}"
        requests.post(f"{BASE_URL}/api/r1/chat", headers=self._headers(self.token),
                     json={"message": "test", "session_id": s})
        resp = requests.delete(f"{BASE_URL}/api/r1/chat/sessions/{s}", headers=self._headers(self.token))
        print(f"Status: {resp.status_code}")
        return resp.status_code == 200

    def test_09_docs_list(self):
        print("\n=== Test 9: Documents ===")
        if not self.token:
            self.test_02_login()
        resp = requests.get(f"{BASE_URL}/api/r1/documents", headers=self._headers(self.token))
        print(f"Status: {resp.status_code}")
        return resp.status_code in [200, 403]

    def test_10_upload(self):
        print("\n=== Test 10: Upload ===")
        test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test_docs")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Test\n\nTest content.")
        try:
            with open(test_file, "rb") as f:
                files = {"file": ("test.md", f, "text/markdown")}
                resp = requests.post(f"{BASE_URL}/api/r1/documents/upload", files=files,
                                   headers={"Authorization": f"Bearer {self.token}"})
            print(f"Status: {resp.status_code}")
            if resp.status_code == 403:
                print("Note: Admin required")
                return True
            return resp.status_code in [200, 201]
        except Exception as e:
            print(f"Error: {e}")
            return False

    def test_11_search(self):
        print("\n=== Test 11: Search ===")
        try:
            from app.rag_utils import retrieve_documents
            from app.config import ARK_API_KEY
            if not ARK_API_KEY:
                print("SKIP: No API key")
                return False
            r = retrieve_documents("test", top_k=3)
            print(f"Found: {len(r.get('docs', []))} docs")
            print(f"Mode: {r.get('meta', {}).get('retrieval_mode')}")
            return True
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_12_rag(self):
        print("\n=== Test 12: RAG Pipeline ===")
        try:
            from app.rag_pipeline import run_rag_graph
            from app.config import ARK_API_KEY
            if not ARK_API_KEY:
                print("SKIP: No API key")
                return False
            r = run_rag_graph("test")
            print(f"Found: {len(r.get('docs', []))} docs")
            return True
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_13_tools(self):
        print("\n=== Test 13: Tools ===")
        try:
            from app.tools import get_current_weather
            print("OK")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def test_14_grade(self):
        print("\n=== Test 14: Grading ===")
        try:
            from langchain.chat_models import init_chat_model
            from app.config import ARK_API_KEY, MODEL, BASE_URL
            from app.rag_pipeline import GradeDocuments
            if not ARK_API_KEY:
                print("SKIP: No API key")
                return False
            model = init_chat_model(model=MODEL, model_provider="openai", api_key=ARK_API_KEY,
                                   base_url=BASE_URL, temperature=0)
            grader = model.with_structured_output(GradeDocuments)
            result = grader.invoke([{"role": "user", "content": "Answer yes or no. Context: test. Question: test. Return a JSON object with a single field 'binary_score' containing 'yes' or 'no'."}])
            print(f"Grade: {result.binary_score}")
            return True
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_15_milvus(self):
        print("\n=== Test 15: Milvus ===")
        try:
            from app.utils.milvus_service import milvus_service
            from app.utils.embedding_service import embedding_service
            
            # 重新创建 collection 确保 schema 正确
            milvus_service.init_collection(force_recreate=True)
            print("Collection recreated")
            
            # 测试插入
            dense = embedding_service.get_embedding("test content")
            sparse = embedding_service.get_sparse_embedding("test content")
            
            test_data = [{
                "text": "test content",
                "filename": "test.txt",
                "file_type": "text",
                "chunk_id": "test_1",
                "parent_chunk_id": "",
                "chunk_level": 3,
                "dense_embedding": dense,
                "sparse_embedding": sparse,
            }]
            
            milvus_service.insert(test_data)
            print("Insert OK")
            
            # 测试搜索
            result = milvus_service.dense_search(dense, 3)
            print(f"Found: {len(result)} docs")
            return True
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all(self):
        print("=" * 50)
        print("RAG Agent API Tests")
        print("=" * 50)
        
        tests = [
            # ("Register", self.test_01_register),
            ("Login", self.test_02_login),
            ("Get Me", self.test_03_get_me),
            ("Chat", self.test_04_chat),
            ("Stream", self.test_05_stream),
            ("Sessions", self.test_06_sessions),
            ("Get Session", self.test_07_get_session),
            ("Delete", self.test_08_delete_session),
            ("Docs List", self.test_09_docs_list),
            ("Upload", self.test_10_upload),
            ("Search", self.test_11_search),
            ("RAG Pipeline", self.test_12_rag),
            ("Tools", self.test_13_tools),
            ("Grading", self.test_14_grade),
            ("Milvus", self.test_15_milvus),
        ]
        
        results = []
        for name, test in tests:
            try:
                r = test()
                results.append((name, r))
                print(f"[{'OK' if r else 'X'}] {name}")
            except Exception as e:
                print(f"[X] {name}: {e}")
                results.append((name, False))
        
        print("\n" + "=" * 50)
        passed = sum(1 for _, r in results if r)
        print(f"Total: {passed}/{len(results)} passed")
        print("=" * 50)


if __name__ == "__main__":
    t = APITester()
    t.run_all()
