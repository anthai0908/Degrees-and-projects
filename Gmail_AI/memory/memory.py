
from fastapi import logger
from matplotlib.pylab import f
from mem0 import AsyncMemory
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv
from backend.utils import encrypt, decrypt
import os
from functools import lru_cache
load_dotenv()
from urllib.parse import quote_plus
from langchain_core.messages import BaseMessage
from backend.utils import logger
from memory.runtime_store import temp_pass
from prompts.tools import load_prompt

ADD_MEMORY_PROMPT =  load_prompt("ADD_MEMORY_PROMPT.md")
class EncryptedAsyncPostgresSaver(AsyncPostgresSaver):
    def __init__(self, connection_pool: AsyncConnectionPool):
        super().__init__(connection_pool)

    def _encrypt_message(self, config, checkpoint):
        checkpoint = checkpoint.copy()
        checkpoint["channel_values"] = checkpoint["channel_values"].copy()
        user_id_str = config["configurable"]["thread_id"]
        login_password = temp_pass[user_id_str]
        messages = checkpoint["channel_values"].get("messages", [])
        if lt :=checkpoint["channel_values"].get("long_term_mem"):
            checkpoint["channel_values"]["long_term_mem"] = encrypt(lt, user_id_str, login_password)
        for i, message in enumerate(messages):
            if isinstance(message, dict) and "content" in message:
                original_content = message["content"]
                encrypted_content = encrypt(original_content, user_id_str, login_password)
                checkpoint["channel_values"]["messages"][i]["content"] = encrypted_content
        return checkpoint
    
    @lru_cache(maxsize=512)
    def _cached_decrypt(encrypted_data: str, user_id_str: str, password: str) -> str:
        """Decrypts data with caching to optimize repeated access."""
        return decrypt(encrypted_data, user_id_str, password)
    
    async def alist(self, config, *, filter, before, limit):
        async for item in super().alist(config, filter=filter, before=before, limit=limit):
            yield item


        
    async def aget_tuple(self, config):
        await super().aget_tuple(config)
    
    
    async def aput_writes(self, config, writes, task_id, task_path = ""):
        return await super().aput_writes(config, writes, task_id, task_path)
    
    async def aget_tuple(self, config):
        return await super().aget_tuple(config)
    
    async def adelete_thread(self, thread_id):
        return await super().adelete_thread(thread_id)

    async def aput(self, config, checkpoint, task_id, task_path = ""):
        encrypted_checkpoint = self._encrypt_message(config, checkpoint)
        return await super().aput(config, encrypted_checkpoint, task_id, task_path)
    
    async def _load_checkpoint_tuple(self, value):
        result = await super()._load_checkpoint_tuple(value)
        
        if result is not None:
            user_id_str = result.config["configurable"]["thread_id"]
            login_password = temp_pass[user_id_str]
            for m in result.checkpoint["channel_values"].get("messages", []):
                if "content" in m:
                    m["content"] = self._cached_decrypt(m["content"], user_id_str, login_password)
            if "long_term_mem" in result.checkpoint["channel_values"]:
                result.checkpoint["channel_values"]["long_term_mem"] = self._cached_decrypt(result.checkpoint["channel_values"]["long_term_mem"], user_id_str, login_password)
        return result
class MemoryService:
    def __init__(self):
            self.connection_pool = None
            self.long_term_memory = None
            self.checkpointer = None 
            self.memory_config = {
                "llm": {
                   "provider" : "openai",
                   "config": {
                       "model" : "Qwen3-8B-Q8_0.gguf",
                       "api_key": "dummy",
                       "temperature": 0.3,
                       "max_tokens": 8192, 
                       "openai_base_url": f"http://localhost:{os.getenv("PORT")}/v1",
                       "top_p": 0.95,
                       "top_k": 40
                   }
                },
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        "user": f"{os.getenv("DB_USER")}",
                        "password": f"{os.getenv("DB_PASSWORD")}",
                        "host": f"{os.getenv("DB_HOST")}",
                        "port": f"{os.getenv("DB_PORT")}",
                        "dbname": os.getenv("DB_NAME"),
                        "embedding_model_dims": os.getenv("MEMORY_VECTOR_DIM")
                        
                    }
                },
                "embedder": {
                    "provider": "huggingface",
                    "config": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2",
                    }
                },
                "custom_fact_extraction_prompt" : ADD_MEMORY_PROMPT,
                
                "reranker": {
                    "provider": "huggingface",
                    "config": {
                        "model": "BAAI/bge-reranker-base",
                        "device": "cpu",
                        "batch_size": 8
                    }
                }
            }
            self.connection_pool_config = {
                "conninfo" :  "postgresql://"\
                f"{quote_plus(os.getenv("DB_USER"))}:{quote_plus(os.getenv("DB_PASSWORD"))}"\
                f"@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}",
                "open": False,
                "max_size": 5,
                "kwargs": {
                    "autocommit": True
                }
            }
    
    async def init_memory(self):
        self.connection_pool = AsyncConnectionPool(**self.connection_pool_config)
        await self.connection_pool.open()
        self.checkpointer = EncryptedAsyncPostgresSaver(self.connection_pool)
        await self.checkpointer.setup()
        self.long_term_memory = await AsyncMemory.from_config(self.memory_config)
        
    async def safe_add_memory(self, user_id_str, messages : list[BaseMessage]):
        try:
            text_messages = "\n".join([
            f"{m.type}: {m.content}" for m in messages if m.content
            ])
            await self.long_term_memory.add(
                user_id=user_id_str,
                messages=text_messages,
            )
        except Exception as e:
            logger.error(f"Error adding memory for user {user_id_str}: {str(e)}")
            print(f"Error adding memory for user {user_id_str}: {e}")        
memoryservice = MemoryService()          


           
