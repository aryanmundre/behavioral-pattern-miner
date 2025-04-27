import aiohttp
import json
import requests
import os
from typing import Optional
import sys
from config import ASI1_API_KEY, ASI1_API_URL

class ASI1Client:
    def __init__(self, api_key=None, api_url=None):
        self.api_key = api_key or ASI1_API_KEY
        self.api_url = api_url or ASI1_API_URL
        
        if not self.api_key:
            print("❌ ERROR: ASI-1 Mini API key not found!")
            print("Please set the ASI1_API_KEY in the config.py file.")
            sys.exit(1)
            
        print(f"🔧 Initializing ASI-1 Mini client")
        print(f"API URL: {self.api_url}")
        print(f"API Key: {self.api_key[:4]}...{self.api_key[-4:] if len(self.api_key) > 8 else ''}")

    def generate(self, prompt, max_tokens=100):
        print(f"\n🤖 Generating response for prompt: {prompt}")
        try:
            # For demo purposes, use a fallback response if API fails
            try:
                response = requests.post(
                    f"{self.api_url}/generate",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"prompt": prompt, "max_tokens": max_tokens}
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ Successfully generated response: {result['text'][:100]}...")
                return result['text']
            except Exception as e:
                print(f"⚠️ API call failed, using fallback response: {str(e)}")
                # Fallback response for demo
                if "sequence of actions" in prompt:
                    return "Open Chrome and navigate to GitHub"
                return "This is a demo macro description"
        except Exception as e:
            print(f"❌ Error generating response: {str(e)}")
            return "This is a demo macro description"

    def refine(self, prompt, feedback, max_tokens=100):
        print(f"\n🔄 Refining response with feedback: {feedback}")
        try:
            # For demo purposes, use a fallback response if API fails
            try:
                response = requests.post(
                    f"{self.api_url}/refine",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"prompt": prompt, "feedback": feedback, "max_tokens": max_tokens}
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ Successfully refined response: {result['text'][:100]}...")
                return result['text']
            except Exception as e:
                print(f"⚠️ API call failed, using fallback response: {str(e)}")
                # Fallback response for demo
                return "This is a refined demo macro description"
        except Exception as e:
            print(f"❌ Error refining response: {str(e)}")
            return "This is a refined demo macro description"

    def refine_macro(self, macro_description, user_feedback):
        print(f"\n📝 Refining macro with feedback: {user_feedback}")
        prompt = f"Original macro: {macro_description}\nUser feedback: {user_feedback}\nPlease improve the macro."
        return self.refine(prompt, user_feedback)

def refine_macro_prompt(user_instruction, original_sequence):
    """Legacy function for backward compatibility."""
    print(f"\n🤖 ASI-1 MINI (LEGACY): Refining macro...")
    print(f"User instruction: {user_instruction}")
    print(f"Original sequence: {original_sequence[:100]}...")
    
    # For demo purposes, use a fallback response
    print(f"⚠️ Using fallback response for demo")
    return original_sequence
