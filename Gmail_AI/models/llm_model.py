from langchain_openai import ChatOpenAI
from langfuse.openai import OpenAI
import os
from dotenv import load_dotenv
from langgraph.prebuilt import InjectedState
from typing import Literal, Optional
from backend.utils import logger
import asyncio
from models.message_model import MessageModel
from langchain.tools import tool
from database.db import dbservice
from backend.utils import decrypt
from memory.runtime_store import temp_pass
from redis_client.redis_client import redis_client
from utils.mail_utils import full_emails_fetch, build_query, MESSAGES_ENDPOINT, EMAIL_SUMMARY_PROMPT
from backend.utils import request_access_token, encrypt
import httpx
import base64
import json
from utils.mail_utils import full_emails_fetch, build_query, MESSAGES_ENDPOINT 
from backend.utils import request_access_token
from typing_extensions import Annotated
from models.state import graphState
from email.utils import parseaddr
from email.message import EmailMessage
from backend.utils import safe_send, send_message as telegram_send_message
import re
load_dotenv("../.env")
from git import Repo
llm = ChatOpenAI(
    base_url=os.getenv("LLM_URL_path"),
    api_key="not-needed", 
    model="local-model",
    temperature=0.3,
    top_p=0.9,
    max_completion_tokens=32000,
    max_tokens=65000
)



async def email_summarise(email: dict) -> dict:
    
    if email is None:
        raise ValueError("Failed during retrieve email, email is None")

    if not email:
        return {
            "email_id": "N/A",
            "summary": "No email content to summarize",
            "need_to_solve": "0"
        }

    # 🔹 Call LLM
    prompt = EMAIL_SUMMARY_PROMPT + "\n" + json.dumps(email, ensure_ascii=False, default=str) 
    response = await llm.ainvoke([
        prompt
    ])

    content = response.content  # ✅ string
    # 🔹 Safe JSON parsing
    print(f"content is: \n{content}")
    parsed_content = parse_content(content)

    
   


    print(f"Need to solve is: {parsed_content["need_to_solve"]}")
    need_to_solve = parsed_content["need_to_solve"]
    if need_to_solve is True:
        message = MessageModel(
            message_id=email["message_id"],
            thread_id=email["thread_id"],
            user_id=email["user_id"],
            sender=email["sender"],
            subject=email["subject"],
            date=email["date"],
            content=encrypt(
                parsed_content["summary"],
                email["user_id"],
                temp_pass.get(email["user_id"])
            )
        )
        await dbservice.add_message(message)
    return parsed_content
    
@tool 
async def get_unsolved_messages(state : Annotated[graphState, InjectedState]) -> list[MessageModel]:
    """Get unsolved messages from the database for a given user_id

    Args:
        state: Current state of the graph to retrieve user_id

    Returns:
        list[MessageModel]: list of unsolved messages
    """
    user_id = state.user_id
    unsolved_messages = await dbservice.get_unsolved_messages(user_id=user_id)
    for msg in unsolved_messages:
        msg.content = decrypt(msg.content, msg.user_id, temp_pass.get(msg.user_id))
    return unsolved_messages

@tool 
async def handle_message(
    state: Annotated[graphState, InjectedState],
    message_id: Optional[str] = None,
    action: Literal["reply", "delete", "forward"] = "reply",
    content: Optional[str] = None,
    subject: Optional[str] = None,
    recipient: Optional[list[str]] = None
) -> dict:
    """Use to handle request from user

    Args:
        state used to get user_id
        message_id (str): use to retrieve message need to handle
        action (Literal[&quot;reply&quot;, &quot;delete&quot;, &quot;forward&quot;], optional): Action required from user. Defaults to "reply".
        content (Optional[str], optional): Content of action if needed. Defaults to None.
        subject (Optional[str], optional): Subject of email if needed. Defaults to None.
        recipient (Optional[list[str]], optional): List of recipients of email if needed. Defaults to None.

    Returns:
        dict: _description_
    """
    try:
        if action == "reply":
            await reply_to_message(state=state, message_id=message_id, content=content)

        elif action == "delete":
            await delete_message(state, message_id=message_id)

        elif action == "forward":
            await forward_message(state, message_id=message_id, content=content)
        else:
            return {
                "status": "error",
                "message": f"Invalid action: {action}"
            }

        # ✅ success
        return {
            "status": "ok",
            "action": action,
            "message_id": message_id 
        }

    except Exception as e:
        logger.error(f"Error occurred while handling message {message_id} for user {state.user_id} with action {action}: {str(e)}")
      
        return {
            "status": "error",
            "action": action,
            "message_id": message_id,
            "message": str(e)
        } 
@tool
async def full_fetch_and_summarize_email(state: Annotated[graphState, InjectedState], labels: list[str]= ["inbox"], unread=True, days=7) -> str:
    """Use to fetch and summarise all of unread emails in gmail, then categorise it whether action needed to solve the email

    Args:
        state (Annotated[graphState, InjectedState]): state of the graph.
        labels (list[str]): List of folders of gmail to fetch emails from.
        unread (bool): Whether to include only unread emails. Defaults to True.
        days (int): The number of days to look back for emails. Defaults to 7.

    Returns:
        list[dict]: A list of dictionaries containing email IDs and their summaries.
    """
    print("=== TOOL RUN ===")
    try:
        state.tool_used = True
        user_id_str = state.user_id
        emails = await full_emails_fetch(user_id_str, query=build_query(labels=labels, unread=unread, days=days))
        tasks = [asyncio.create_task(email_summarise(email)) for email in emails]
        summarised_emails = await asyncio.gather(*tasks)
        summary = ""
    

        for i in range(len(summarised_emails)):
            summary += (
                f"Email ID: {summarised_emails[i]['email_id']}\n"
                f"Summary: {summarised_emails[i]['summary']}\n\n"
            )

            # send every 3 emails
            if (i + 1) % 3 == 0:
                if summary.strip():
                    await safe_send(telegram_send_message, user_id_str, summary)
                summary = ""

        # send remaining
        if summary.strip():
            await safe_send(telegram_send_message, user_id_str, summary)
        return (f"Have {len(summarised_emails)} unread messages, all are fetched, summarised and sent to user")
    except Exception as e:
        logger.error(f"Error during fetch and summarise unread emails: {str(e)}")
        return (f"An error during fetching and summarise unread emails: {str(e)}")

async def reply_to_message(state: Annotated[graphState, InjectedState], message_id: str, content: str):
    user_id_str = state.user_id
    access_token = await redis_client.get(f"{user_id_str}_access_token")
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))

    message = await dbservice.get_message_by_id(message_id)
    if not message:
        raise ValueError(f"Message with id {message_id} not found")
    _, sender = parseaddr(message.sender)
    print(f"sender is {sender}")
    if not sender:
        raise ValueError(f"Invalid sender email: {message.sender}")
    # 🔥 Build proper MIME message
    msg = EmailMessage()
    msg["To"] = sender
    msg["From"] = "me"
    msg["Subject"] = f"Re: {message.subject or '(no subject)'}"
    msg["In-Reply-To"] = message.message_id
    msg["References"] = message.message_id

    msg.set_content(content)

    encoded_message = base64.urlsafe_b64encode(
        msg.as_bytes()
    ).decode()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "raw": encoded_message,
        "threadId": message.thread_id
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{MESSAGES_ENDPOINT}/send",
            headers=headers,
            json=payload
        )

        # 🔥 print Gmail error details if any
        if response.status_code != 200:
            print("GMAIL ERROR:", response.text)

        response.raise_for_status()

    await dbservice.delete_message_by_id(message_id)


async def delete_message(state: Annotated[graphState, InjectedState], message_id: str):
    user_id_str = state.user_id
    access_token = await redis_client.get(f"{user_id_str}_access_token")
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.delete(f"{MESSAGES_ENDPOINT}/{message_id}", headers=headers)
        response.raise_for_status()


async def forward_message(state: Annotated[graphState, InjectedState], message_id: str, content: str):
    user_id_str = state.user_id
    access_token = await redis_client.get(f"{user_id_str}_access_token")
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))
    message = await dbservice.get_message_by_id(message_id)
    if not message:
        raise ValueError(f"Message with id {message_id} not found")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "raw": base64.urlsafe_b64encode(content.encode("utf-8")).decode("utf-8"),
        "threadId": message.thread_id,
        "to": content,  # here content is the email address to forward to
        "subject": f"Fwd: {message.subject}"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{MESSAGES_ENDPOINT}/send", headers=headers, json=payload)
        response.raise_for_status()

@tool
async def send_message(state: Annotated[graphState, InjectedState], recipient: list[str], subject: str, content: str)->str:
    """Use to send an email to a list of recipients

    Args:
        state (Annotated[graphState, InjectedState]): state of the graph to retrieve user_id
        recipient (list[str]): list of recipients 
        subject (str): The subject of the email
        content (str): The content of the email

    Returns:
        str: Status of sending message
    """
    user_id_str = state.user_id
    user = await dbservice.get_user(user_id=user_id_str)
    user_email = user.e_mail



    access_token = await redis_client.get(f"{user_id_str}_access_token")
    if not access_token:
        access_token = await request_access_token(user_id_str, temp_pass.get(user_id_str))
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
        }
    msg = EmailMessage()
    msg["To"] = ", ".join(recipient)
    msg["From"] = user_email
    msg["Subject"] = subject
    msg.set_content(content)
    
    payload = {
        "raw": base64.b64encode(msg.as_bytes()).decode("utf-8")
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(f"{MESSAGES_ENDPOINT}/send", headers=headers, json=payload)
            response.raise_for_status()
            return f"Successfully sent email to {recipient}"
        except Exception as e:
            logger.error(f"Failed to ")
            return f"Failed to send email to {recipient}: {str(e)}"
            
        
def parse_content(text: str) -> dict:
    email_id = re.search(r"email_id\s*(.*?)\s*<endofemailid>", text).group(1)
    summary = re.search(r"summary\s*(.*?)\s*<endofsummary>", text).group(1)
    need_to_solve = re.search(r"need_to_solve\s*(.*?)\s*<endofneedtosolve>", text).group(1)

    return {
        "email_id": email_id,
        "summary": summary,
        "need_to_solve": need_to_solve == "1"
    }
tools = [full_fetch_and_summarize_email, get_unsolved_messages, handle_message, send_message]

llm = llm.bind_tools(tools)
