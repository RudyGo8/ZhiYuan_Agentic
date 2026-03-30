"""
RAG Agent API 接口测试
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_register():
    """测试1: 注册"""
    print("\n=== 测试1: 用户注册 ===")
    resp = requests.post(f"{BASE_URL}/api/r1/auth/register", json={
        "username": "test_user",
        "password": "test123456"
    })
    print(f"状态: {resp.status_code}")
    print(f"响应: {resp.json()}")
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


def test_login():
    """测试2: 登录"""
    print("\n=== 测试2: 用户登录 ===")
    resp = requests.post(f"{BASE_URL}/api/r1/auth/login", json={
        "username": "test_user",
        "password": "test123456"
    })
    print(f"状态: {resp.status_code}")
    print(f"响应: {resp.json()}")
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


def test_me(token):
    """测试3: 获取当前用户"""
    print("\n=== 测试3: 获取当前用户 ===")
    resp = requests.get(f"{BASE_URL}/api/r1/auth/me", headers={"Authorization": f"Bearer {token}"})
    print(f"状态: {resp.status_code}")
    print(f"响应: {resp.json()}")


def test_chat(token):
    """测试4: 聊天"""
    print("\n=== 测试4: 聊天 ===")
    resp = requests.post(f"{BASE_URL}/api/r1/chat", headers={"Authorization": f"Bearer {token}"}, json={
        "message": "你好，请介绍一下你自己",
        "session_id": "test_session"
    })
    print(f"状态: {resp.status_code}")
    data = resp.json()
    print(f"响应: {data.get('response', '')[:100]}...")


def test_sessions(token):
    """测试5: 会话列表"""
    print("\n=== 测试5: 会话列表 ===")
    resp = requests.get(f"{BASE_URL}/api/r1/chat/sessions", headers={"Authorization": f"Bearer {token}"})
    print(f"状态: {resp.status_code}")
    print(f"响应: {resp.json()}")


if __name__ == "__main__":
    print("=" * 50)
    print("RAG Agent API 接口测试")
    print("=" * 50)

    # 1. 先尝试登录，失败则注册
    token = test_login()
    if not token:
        print("\n登录失败，尝试注册...")
        token = test_register()
    
    if not token:
        print("\n❌ 无法获取token，测试终止")
        exit(1)

    # # 2. 测试其他接口
    # test_me(token)
    # test_chat(token)
    # test_sessions(token)

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
