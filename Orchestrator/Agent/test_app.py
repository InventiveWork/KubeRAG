import requests
import os

def test_langchain_agent():
    url = "http://localhost/langchain/api/chat"
    data = {"input": "hello"}
    response = requests.post(url, json=data)
    assert response.status_code == 200
    assert "hello" in response.json()

def test_llamaindex_agent():
    url = "http://localhost/llamaindex/api/chat"
    data = {"input": "hello"}
    response = requests.post(url, json=data)
    assert response.status_code == 200
    assert "hello" in response.json()

def test_gemini_agent():
    url = "http://localhost/gemini/api/chat"
    data = {"input": "hello"}
    response = requests.post(url, json=data)
    assert response.status_code == 200
    assert "hello" in response.json()

def test_semantic_kernel_agent():
    url = "http://localhost/semantic-kernel/api/chat"
    data = {"input": "hello"}
    response = requests.post(url, json=data)
    assert response.status_code == 200
    assert "hello" in response.json()
