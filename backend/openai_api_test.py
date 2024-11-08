import openai
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set the OpenAI API key
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Test the API key with a simple request
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print("API call successful. Response:", response['choices'][0]['message']['content'])
except Exception as e:
    print("API call failed:", e)