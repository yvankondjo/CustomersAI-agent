import os
from dotenv import load_dotenv


load_dotenv()

class Settings:
    PROJECT_NAME: str = "SocialSync AI"
    PROJECT_VERSION: str = "1.0.0"

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    SUPABASE_JWT_ALGORITHM: str = "HS256"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_CONFIG_ID: str = os.getenv("META_CONFIG_ID", "test")
    META_GRAPH_VERSION: str = os.getenv("META_GRAPH_VERSION", "v24.0")
    WHATSAPP_REDIRECT_URI: str = os.getenv("WHATSAPP_REDIRECT_URI", "test")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "tests")
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not SUPABASE_ANON_KEY or not SUPABASE_JWT_SECRET:
        raise ValueError("SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY and SUPABASE_JWT_SECRET environment variables are required")

def get_settings() -> Settings:
    settings = Settings() 
    return settings
