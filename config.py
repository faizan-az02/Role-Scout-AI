import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

def get_llm():
    return LLM(
        model=os.getenv("MODEL"),
        api_key=os.getenv("API_KEY"),
        base_url="https://models.inference.ai.azure.com",
        temperature=0.2
    )