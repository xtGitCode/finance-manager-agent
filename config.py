import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # plaid
    PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
    PLAID_SECRET = os.getenv("PLAID_SECRET")
    PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
    
    # tavily 
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # llm 
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    def validate(cls):
        required_keys = [
            (cls.PLAID_CLIENT_ID, "PLAID_CLIENT_ID"),
            (cls.PLAID_SECRET, "PLAID_SECRET"),
            (cls.TAVILY_API_KEY, "TAVILY_API_KEY"),
        ]
        if cls.LLM_PROVIDER == "groq":
            required_keys.append((cls.GROQ_API_KEY, "GROQ_API_KEY"))
        elif cls.LLM_PROVIDER == "openai":
            required_keys.append((cls.OPENAI_API_KEY, "OPENAI_API_KEY"))
        
        missing_keys = [key_name for key_value, key_name in required_keys if not key_value]
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        return True

config = Config()