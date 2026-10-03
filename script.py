import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")
client = Groq(api_key=api_key)
models = client.models.list()
model = models.data[0].id
print("Using model:", model)
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model=model,
)
print("\nAI Response:")
print(chat_completion.choices[0].message.content)
