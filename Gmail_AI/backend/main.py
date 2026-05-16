import asyncio

from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from database.db import dbservice
from models.chat_message import Update
from database.db import dbservice
from redis_client.redis_client import redis_client
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from backend.utils import request_access_token, send_message, send_auth_url, safe_send,  request_tokens, verify_id_token, hash_password
from graph.graph import build_graph
from memory.memory import memoryservice
from urllib.parse import urlencode
from models.user_model import UserModel
import os
import httpx
import logging
from memory.runtime_store import temp_pass
from langfuse_client.langfuse import langfuse_client
from langfuse import Langfuse
load_dotenv(dotenv_path="../.env")

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    base_url=os.getenv("LANGFUSE_BASE_URL"),
)
LOGGING_REQUEST= "PLEASE INPUT YOUR PASSWORD WITH SYNTAX \nREFRESH_PASSWORD: YOUR_PASSWORD_HERE"
REGISTER_REQUEST = "USER NOT FOUND, PLEASE INPUT YOUR LOGIN PASSWORD WITH SYNTAX\n REGISTRATION_PASSWORD: <YOUR_LOGIN_PASSWORD_HERE>"
AUTHORISATION_REQUST = "PLEASE CLICK TO REGISTER"
LOGGING_NOTIFICATION = "LOGGING SUCCESSFUL, YOU CAN NOW INTERACT WITH THE BOT"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

processed_updates = set()
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis_client
    
    await dbservice.init_db()
    await memoryservice.init_memory()
    builder = build_graph()
    app.state.graph = builder.compile(checkpointer=memoryservice.checkpointer)
    
    yield
    await dbservice.close()
    await app.state.redis.aclose()
    langfuse.flush()
app = FastAPI(
    lifespan=lifespan
)

@app.post("/chat")
async def chat(request: Request, update: Update):
    if update.update_id in processed_updates:
        print("UPDATE ID:", update.update_id)
        return {"ok": True}
    processed_updates.add(update.update_id)
    try:
        redis = request.app.state.redis
        graph = request.app.state.graph
        user_text = update.message.content
        user_id = update.message.chat.id
        user_id_str = str(user_id)
        user = await dbservice.get_user(user_id_str)
        if(user):
            access_token = await redis.get(f"{user_id_str}_access_token")
            
            if(access_token):
                print("access Token exists in redies, checking temp password of user id")
                if user_id_str not in temp_pass:
                    print("temp pass does not have user_id_str, inserting password")
                    if user_text.startswith("REFRESH_PASSWORD:"):
                        password = user_text.split("REFRESH_PASSWORD:")[1].strip()
                        temp_pass[user_id_str] = password
                        await safe_send(send_message, chat_id=user_id, text=LOGGING_NOTIFICATION)
                    else:
                        await safe_send(send_message, chat_id=user_id, text=LOGGING_REQUEST)
                else:
                    print("temp pass has user_id_str")
                    memory_client = memoryservice.long_term_memory
                    long_term_mem = await memory_client.search(query=user_text, user_id=user_id_str, limit=5)
                    memory_context = "\n".join([f"* {res['memory']}" for res in long_term_mem.get("results", [])])
                    response = await graph.ainvoke(
                        {   "user_id": user_id_str,
                            "messages": [HumanMessage(content=user_text)],
                            "long_term_mem": memory_context or "No relevant memories found.",
                            "login_password": temp_pass[user_id_str],
                        },
                        config = {
                            "configurable": {
                                "thread_id": user_id_str
                            },
                            "callbacks": [langfuse_client]
                        })
                    langfuse.flush()
                    asyncio.create_task(memoryservice.safe_add_memory(user_id_str, response["messages"]))
                    await safe_send(send_message, chat_id=user_id, text=response["messages"][-1].content)
                    return {"ok": True}
            else:
                print("access token expired, requesting new access token")
                if user_text.startswith("REFRESH_PASSWORD:"):
                    password = user_text.split("REFRESH_PASSWORD:")[1].strip()
                    temp_pass[user_id_str] = password
                    await safe_send(request_access_token, user_id_str, password)
                    await safe_send(send_message, chat_id=user_id, text=LOGGING_NOTIFICATION)
                else:
                    await safe_send(send_message, chat_id=user_id, text=LOGGING_REQUEST)
                return {"ok":True}

        else: 
            if user_text.startswith("REGISTRATION_PASSWORD:"):
                password = user_text.split("REGISTRATION_PASSWORD:")[1].strip()
                temp_pass[user_id_str] = password
                await safe_send(send_auth_url, user_id_str)
                return {"ok": True}
            await safe_send(send_message, chat_id=user_id, text=REGISTER_REQUEST)
    except Exception as e:
        logging.exception(f"Error processing chat message: {str(e)}")

                    
            
@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state in callback")
    user_id_str = state
    tokens = await request_tokens(code, user_id_str, temp_pass.get(user_id_str))
    if tokens:
        user = await dbservice.get_user(user_id_str)
        if user:
            await redis_client.set(f"{user_id_str}_access_token", tokens["access_token"], ex=900)
            await safe_send(send_message, chat_id=user_id_str, text=LOGGING_NOTIFICATION)
            return {
                "ok": True,
                "message": "User already exists back, back to telegram bot to use the bot"}
            
        raw_id_token = tokens.get("id_token")
        decoded = await verify_id_token(raw_id_token)
        if decoded["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise Exception("Invalid issuer")
        if not decoded.get("email_verified", False):
            raise Exception("Email not verified")
        email = decoded.get("email")
        hashed_password = hash_password(temp_pass.get(user_id_str))
        await dbservice.add_user(UserModel(user_id=user_id_str, e_mail=email, encrypted_refresh_token=tokens["encrypted_refresh_token"], hashed_password=hashed_password))
        await redis_client.set(f"{user_id_str}_access_token", tokens["access_token"], ex=900)  # 15 min expiry
        await safe_send(send_message,chat_id=user_id_str, text=LOGGING_NOTIFICATION)
        return {"ok": True,
                "message": "User created, back to telegram bot to use the bot"}
    # Process the authorization code, exchange for tokens, and store in 
