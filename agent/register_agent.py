# register_agent.py

import requests

# --- 1. Your Agentverse API Key ---
AGENTVERSE_API_KEY = "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3NDgyOTg5ODUsImlhdCI6MTc0NTcwNjk4NSwiaXNzIjoiZmV0Y2guYWkiLCJqdGkiOiI2ODAyZjk0MDk1Nzg1YzJkYTdlOTMyOTUiLCJzY29wZSI6ImF2Iiwic3ViIjoiNzU2OWZiMWE1NmI2YzMyMzg4MjBlZWMzMGJkNzE3MzcwYTg1YTg0YjBhYWJkMDM0In0.Ap9swjbqxRvUnDXy89vCfz8F9Qz6D4fiK8MPTWrB3YGDqkZP-WCkO_8TcMRw-M9piNZ41a2yxgwCHWIz2BlCuYzAWmKvVnQH5e78cio6VWE6Bc-095arnstFhRcvmBy2VcastFHTZAl6-rW3jzG2y8Pp8NB8qJ-35X9R1lcNbm66TQSiPvNhgGOzvivf5w7CtirgpJuSS4mp70u_OA9QnexgO_QyNkrg2ViUMVgw-awnq0EXQQs_80ciIrCp_k_BAYHKRoBIIFjWhppTNqHDlXqqxZbNoM4RYJ077oMfczcgzh3PZJPxK65KBgSMd2ezRtQ06dfyt8Vc-CWbBXAAyw"  # <-- Replace this!

# --- 2. Your Agent Metadata ---
payload = {
    "name": "Dynamic Workflow Trainer",
    "description": "An AI agent that detects user workflows and helps users refine them into smart macros using ASI-1 Mini LLM.",
    "tags": ["Productivity", "Automation", "AI Agents", "ASI1"],
    "endpoint": "http://127.0.0.1:8001/submit"   # localhost during hackathon
}

# --- 3. HTTP Headers ---
headers = {
    "Authorization": f"Bearer {AGENTVERSE_API_KEY}",
    "Content-Type": "application/json"
}

# --- 4. POST to Agentverse API ---
response = requests.post(
    "https://api.agentverse.ai/v1/agents",
    headers=headers,
    json=payload
)

# --- 5. Print Result ---
if response.status_code == 200 or response.status_code == 201:
    print("✅ Successfully registered your agent on Agentverse!")
    print("Agent ID:", response.json().get("id", "Unknown"))
else:
    print(f"❌ Registration failed. Status code: {response.status_code}")
    print(response.text)
