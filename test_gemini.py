import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

model_name = os.getenv("GEMINI_MODEL")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is missing from .env")

if not model_name:
    raise ValueError("GEMINI_MODEL is missing from .env")

llm = ChatGoogleGenerativeAI(
    model=model_name,
    temperature=0,
    max_retries=2,
)

response = llm.invoke(
    "Write one PostgreSQL SELECT query to count all customers "
    "in a table named customer. Return SQL only."
)

print(response.content)
print("\nToken usage:", response.usage_metadata)