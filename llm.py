import os
import requests
from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL

def query_groq_llm(prompt, system_prompt=None):
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        'model': GROQ_MODEL,
        'messages': [
            {"role": "system", "content": system_prompt or "You are a helpful agricultural assistant."},
            {"role": "user", "content": prompt}
        ],
        'max_tokens': 512,
        'temperature': 0.7
    }
    print("Querying Groq LLM...")
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    text = result['choices'][0]['message']['content'].strip()
    print(f"LLM Response: {text}")
    return text

if __name__ == "__main__":
    query_groq_llm("What is the best time to sow wheat in Punjab?")
