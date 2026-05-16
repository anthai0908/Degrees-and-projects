import asyncio
from models.state import graphState
from langchain_core.messages import trim_messages, SystemMessage
from typing import Union
from pathlib import Path
import json
from datetime import datetime
import os
from llama_cpp import Llama
from transformers import AutoTokenizer
from prompts.tools import load_prompt
llm_tokenizer = AutoTokenizer.from_pretrained("google/gemma-7b")
global cache
cache = {}

def token_counter(messages):
    total = 0
    for m in messages:
        key = m.content 
        if key not in cache:
            text = f"{m.type}: {m.content}"
            cache[key] = len(llm_tokenizer.tokenize(text))
            total+=cache[key]
    return total


SYSTEM_PROMPT = load_prompt("SYSTEM_PROMPT.md")

def get_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def graph_trim_message(state: graphState):
    trimmed_messages = trim_messages(
        state.messages,
        max_tokens=16000- 1024,
        token_counter=token_counter,
        strategy="last",
        include_system=False,
        start_on=None,  # ✅ FIX
        allow_partial=False
    )

    long_memory = state.long_term_memory
    datetime = get_datetime()
    system_prompt = SYSTEM_PROMPT.format(
        long_memory=long_memory,
        current_time=datetime
    )

    # remove old system if exists
    if trimmed_messages and trimmed_messages[0].type == "system":
        trimmed_messages = trimmed_messages[1:]

    return graphState(
    **{**state.model_dump(), "messages": [SystemMessage(content=system_prompt), *trimmed_messages]}
    )



    