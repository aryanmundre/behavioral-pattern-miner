import requests
import json

ASI1_API_KEY = "sk_7ffa5e40c15b48fd9da6173d6c735c0b3eede2f5fa964d2d8a86a6926dc6b92d"
ASI1_API_URL = "https://api.asi1.ai/v1/chat/completions"

def test_asi1(prompt):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {ASI1_API_KEY}"
    }
    payload = {
        "model": "asi1-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "stream": False,
        "max_tokens": 200
    }
    response = requests.post(ASI1_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        print("✅ Success!")
        print("Response:", response.json()["choices"][0]["message"]["content"])
    else:
        print("❌ Error:", response.status_code, response.text)

if __name__ == "__main__":
    test_prompt = "User wants to modify the workflow: VS Code → GitHub → Slack. Instruction: Add Notion after GitHub."
    test_asi1(test_prompt)
