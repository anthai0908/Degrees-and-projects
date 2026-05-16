from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv
import os

load_dotenv("../.env")

langfuse_client = CallbackHandler()