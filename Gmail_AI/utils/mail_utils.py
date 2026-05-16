import base64
import httpx
from .graph_utils import load_prompt
from redis_client.redis_client import redis_client
import json
import asyncio
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
import html
from database.db import dbservice

from backend.utils import encrypt, decrypt
from memory.runtime_store import temp_pass
from langchain.tools import tool
from backend.utils import request_access_token
 
EMAIL_SUMMARY_PROMPT = load_prompt("EMAIL_SUMMARY_PROMPT.md")
MESSAGES_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

 # limit concurrent API calls to 10

def clean_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")

    # Remove useless tags
    for tag in soup(["script", "style", "head", "meta", "title"]):
        tag.decompose()

    # Remove hidden elements safely
    for tag in soup.find_all(True):  # only real tags
        attrs = getattr(tag, "attrs", None)
        if not attrs:
            continue

        style = attrs.get("style")
        if style:
            cleaned = style.replace(" ", "").lower()
            if "display:none" in cleaned:
                tag.decompose()

    # Remove images
    for img in soup.find_all("img"):
        img.decompose()

    text = soup.get_text(separator="\n", strip=True)

    return html.unescape(text)

def extract_body(payload):
    html_parts = []
    text_parts = []

    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if "data" in body:
        decoded = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="ignore")

        if mime == "text/html":
            html_parts.append(clean_html(decoded))
        elif mime == "text/plain":
            text_parts.append(decoded)

    if "parts" in payload:
        for part in payload["parts"]:
            sub = extract_body(part)
            if sub:
                text_parts.append(sub)

    # prefer HTML
    if html_parts:
        return "\n".join(html_parts)

    return "\n".join(text_parts)

def get_header(headers, name):
    for h in headers:
        if h["name"] == name:
            return h["value"]
    return None

def get_body(payload):
    return extract_body(payload) or ""

def build_query(
    labels : list[str]=None,
    unread=True,
    days=7
):
    parts = []

    if labels:
        if len(labels) == 1:
            parts.append(f"in:{labels[0]}")
        else:
            label_query = " OR ".join(f"in:{l}" for l in labels)
            parts.append(f"({label_query})")

    if unread:
        parts.append("is:unread")

    if days:
        parts.append(f"newer_than:{days}d")

    return " ".join(parts)



async  def emails_fetch(user_id_str: str, query: str):
    # 🔥 need to handle pagination for more emails
    # https://developers.google.com/gmail/api/guides/pagination
    access_token = await redis_client.get(f"{user_id_str}_access_token")
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))
    headers = {
        "Authorization": f"Bearer {access_token}"}
    
    all_emails = []
    page_token = None
    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            params = {"q": query, "maxResults": 100}
            if page_token:
                params["pageToken"] = page_token

            response = await client.get(MESSAGES_ENDPOINT, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            messages = data.get('messages', [])
            all_emails.extend(messages)
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        return all_emails


async def full_emails_fetch(user_id_str: str, query: str):
    messages = await emails_fetch(user_id_str, query=query)
    email_data = []
    msg_id_list = []
    access_token = await redis_client.get(f'{user_id_str}_access_token')
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))
    async with httpx.AsyncClient(timeout=20.0) as client:
        for msg in messages:
            msg_id = msg['id']
            thread_id = msg['threadId']
            response = await client.get(f"{MESSAGES_ENDPOINT}/{msg_id}", headers={
                "Authorization": f"Bearer {access_token}"
            })
            response.raise_for_status()
            msg_data = response.json()
            dt = parsedate_to_datetime(get_header(msg_data["payload"]["headers"], "Date"))
            if dt:
                dt = dt.replace(tzinfo=None)
                
            email_data.append({
                "message_id": msg_id,
                "thread_id": thread_id,
                "user_id": user_id_str,
                "sender": get_header(msg_data["payload"]["headers"], "From"),
                "subject": get_header(msg_data["payload"]["headers"], "Subject"),
                "date":dt,
                "content": get_body(msg_data["payload"])
            })
            msg_id_list.append(msg_id)
            with open("emails.json", "w", encoding="utf-8") as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False, default=str)
    await batch_mark_as_read(msg_id_list, access_token=access_token)
    return email_data


    
async def batch_mark_as_read(message_ids: list[str], access_token: str)->str:
    if not message_ids:
        return {"status": "no_ids"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "ids": message_ids,
        "removeLabelIds": ["UNREAD"]
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify",
            headers=headers,
            json=payload
        )

        if res.status_code not in (200, 204):
            print("GMAIL ERROR:", res.text)

        res.raise_for_status()
        print(f"Marked as read {len(message_ids)} emails")

 