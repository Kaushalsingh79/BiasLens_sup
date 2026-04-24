from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model_name="llama-3.1-8b-instant",  # or "llama-3.3-70b-versatile"
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

response = llm.invoke("Say 'API works!'")
print(response.content)