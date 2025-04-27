import aiohttp
import json
from typing import Optional

# 🔥 FIRST define your API key as a STRING
ASI1_API_KEY = "sk_7ffa5e40c15b48fd9da6173d6c735c0b3eede2f5fa964d2d8a86a6926dc6b92d"
ASI1_API_URL = "https://api.asi1.ai/v1/chat/completions"

class ASI1Client:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "http://localhost:8000"  # ASI-1 Mini local endpoint

    async def generate(self, prompt: str) -> str:
        """Generate a response from ASI-1 Mini."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/generate",
                    json={"prompt": prompt},
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        print(f"Error from ASI-1: {response.status}")
                        return "Error generating response"
        except Exception as e:
            print(f"Error connecting to ASI-1: {str(e)}")
            return "Error connecting to ASI-1"

    async def refine(self, prompt: str, feedback: str) -> str:
        """Refine a response based on feedback."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/refine",
                    json={
                        "prompt": prompt,
                        "feedback": feedback
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        print(f"Error from ASI-1: {response.status}")
                        return "Error refining response"
        except Exception as e:
            print(f"Error connecting to ASI-1: {str(e)}")
            return "Error connecting to ASI-1"

def refine_macro_prompt(user_instruction, original_sequence):
    headers = {
        "Authorization": f"Bearer {ASI1_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    prompt = (
        f"Here is a workflow sequence: {original_sequence}. "
        f"User wants to refine it with this instruction: {user_instruction}. "
        f"Update the workflow appropriately and list the new sequence."
    )

    payload = {
        "model": "asi1-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "stream": False,
        "max_tokens": 300
    }

    response = requests.post(ASI1_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"❌ ASI-1 Mini API Error: {response.status_code}, {response.text}")
        return None
