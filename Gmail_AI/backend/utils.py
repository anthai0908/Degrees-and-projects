import asyncio

import httpx
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlencode
from fastapi import HTTPException
import logging
from redis_client.redis_client import redis_client
from database.db import dbservice
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from google.oauth2 import id_token as google_id_token
load_dotenv(dotenv_path="../.env")
from google.auth.transport.requests import Request 
import bcrypt

logger = logging.getLogger(__name__)
# --- Load credentials ---
cred = None
with open("Credentials/creds.json") as f:
    cred = json.load(f)  # ✅ FIX: use json.load, not loads

# --- Config ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

SCOPES = [
    "openid",  # 🔥 THIS enables id_token
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
    
]
MODE = os.getenv("MODE")
# =========================================================
# 🔧 CORE SENDER (reusable)
# =========================================================
async def send_telegram(payload: dict):
    """
        Sends a message payload to the Telegram Bot API.

    Args:
        payload (dict): The message payload to send to Telegram API

    Returns:
        _type_: Response from Telegram API
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(BOT_URL, json=payload)
            response.raise_for_status()
            return response.json()
        
        
# =========================================================
# 📩 SIMPLE MESSAGE
# =========================================================
async def send_message(chat_id: int | str, text: str):
    """Use to send message to user via bot

    Args:
        chat_id (int, str): chat user_id in int format (telegram provides as int)
        text (str): The text message to send
    """
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    await send_telegram(payload)

# =========================================================
# 🔘 BUTTON MESSAGE
# =========================================================
async def send_button(chat_id: int, text: str, reply_markup: dict):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup
    }
    await send_telegram(payload)

# =========================================================
# 🔗 OAUTH URL
# =========================================================
def prepare_auth_url(user_id: str) -> str:
    params = {
        "client_id": cred["web"]["client_id"],
        "redirect_uri": cred["web"]["redirect_uris"][MODE],
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,  # 🔥 map back to user
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

# =========================================================
# 🔘 BUTTON STRUCTURE
# =========================================================
def build_auth_keyboard(auth_url: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🔐 Connect Gmail",
                    "url": auth_url
                }
            ]
        ]
    }

# =========================================================
# 🚀 MAIN ENTRY (SEND AUTH BUTTON)
# =========================================================
async def send_auth_url(user_id_str: str):


    auth_url = prepare_auth_url(user_id_str)
    keyboard = build_auth_keyboard(auth_url)

    await send_button(
        chat_id=int(user_id_str),
        text="Click below to connect your Gmail:",
        reply_markup=keyboard
    )
    
async def safe_send(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
            logger.error(f"Telegram rejected request: {e.response.text}")
            raise HTTPException(
                status_code=400,
                detail="Telegram request failed"
            )

    except httpx.RequestError as e:
        logger.error(f"Network error: {str(e)}")
        raise HTTPException(status_code=503, detail="Telegram service unavailable")

    except Exception as e:
        logger.exception("Unexpected error")  # 🔥 includes stack trace
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def request_access_token(user_id_str: str, password: str):
    user = await dbservice.get_user(user_id_str)
    encrypted_refresh_token = user.encrypted_refresh_token
    hashed_password = user.hashed_password
    if not match_password(password, hashed_password):
        await safe_send(send_message, chat_id=int(user_id_str), text="Incorrect password. Please try again.")
        raise HTTPException(status_code=401, detail="Unauthorized: Incorrect password")
    decrypted_refresh_token = decrypt(encrypted_refresh_token, user_id_str, password)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            os.getenv("TOKEN_URL"),
            data={
                "client_id": cred["web"]["client_id"],
                "client_secret": cred["web"]["client_secret"],
                "refresh_token": decrypted_refresh_token,
                "grant_type": "refresh_token"
            }
        )
        response.raise_for_status()
        new_access_token = response.json().get("access_token")
        if not new_access_token:
            print("Invalid token response:", response)
            raise HTTPException(status_code=500, detail="No access token returned")
        await redis_client.set(f"{user_id_str}_access_token", new_access_token, ex=900)
        return new_access_token
    
async def request_tokens(code: str, user_id_str: str, password: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            os.getenv("TOKEN_URL"),
            data={
                "code": code,
                "client_id": cred["web"]["client_id"],
                "client_secret": cred["web"]["client_secret"],
                "redirect_uri": cred["web"]["redirect_uris"][MODE],
                "grant_type": "authorization_code"
            }
        )
        response.raise_for_status()
        data = response.json()
        data["encrypted_refresh_token"] = encrypt(response.json().get("refresh_token"), user_id_str=user_id_str, password=password)
        return data     
def encrypt(data: str, user_id_str: str, password: str) -> str:
    """Encrypts data using a user-specific key derived from their ID and password.

    Args:
        data (str): Unencrypted data to be encrypted
        user_id_str (str): Unique identifier for the user, used in key derivation
        password (str): User-provided password, used in key derivation

    Returns:
        str: Encrypted data, encoded in base64 for storage
    """
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', (user_id_str + password).encode(), salt, 100000, dklen=32)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, data.encode(), None)
    blob = salt + nonce + encrypted
    return base64.b64encode(blob).decode()


def decrypt(encrypted_data: str, user_id_str: str, password: str) -> str:
    blob = base64.b64decode(encrypted_data)
    salt = blob[:16]
    nonce = blob[16:28]
    ciphertext = blob[28:]
    key = hashlib.pbkdf2_hmac('sha256', (user_id_str + password).encode(), salt, 100000, dklen=32)
    aesgcm = AESGCM(key)
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted.decode() 

async def verify_id_token(raw_id_token: str) -> dict:
    """Verifies the provided ID token and extracts the user's email.

    Args:
            raw_id_token (str): The raw ID token to verify.

    Returns:
        dict: The user's email info dict if the token is valid, otherwise raises an error.
    """
    # Implementation for ID token verification would go here
    return await asyncio.to_thread(
        lambda: google_id_token.verify_oauth2_token(raw_id_token, Request(), cred["web"]["client_id"])
    )

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt.

    Args:
        password (str): The plaintext password to hash.

    Returns:
        str: The hashed password.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def match_password(password: str, hashed_password: str) -> bool:
    """Checks if a plaintext password matches the hashed password.

    Args:
        password (str): The plaintext password to check.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(password.encode(), hashed_password.encode())