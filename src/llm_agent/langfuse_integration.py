import os
from langfuse.langchain import CallbackHandler

def get_langfuse_callback():
    """
    Initializes and returns the Langfuse CallbackHandler if the required
    environment variables are set. Otherwise, returns None.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    
    if public_key and secret_key:
        try:
            if "LANGFUSE_BASE_URL" in os.environ and "LANGFUSE_HOST" not in os.environ:
                os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

            handler = CallbackHandler()
            return handler
        except Exception as e:
            print(f"Failed to initialize Langfuse callback: {e}")
            return None
    
    return None
