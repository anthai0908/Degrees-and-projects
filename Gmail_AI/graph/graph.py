import asyncio

from langgraph.graph import StateGraph
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from models.state import graphState
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from models.llm_model import llm
from utils.graph_utils import graph_trim_message
from models.llm_model import tools
from langgraph.types import Command
def build_graph():
    builder = StateGraph(graphState)


    builder.add_node("llm_chat", llm_chat)

    builder.add_node("tool_call", tool_call)
    builder.set_entry_point("llm_chat")

    builder.add_edge("tool_call", "llm_chat")
    return builder


async def llm_chat(state: graphState, config: RunnableConfig):
    print("=== GRAPH NODE: llm_chat ===")
    trimmed_messages = graph_trim_message(state=state).messages

    response = await llm.ainvoke(trimmed_messages)

    # 🔥 prevent repeated tool calls
    if state.tool_used:
        return Command(
            update={"messages": [response]},
            goto=END
        )

    return Command(
        update={"messages": [response]},
        goto="tool_call" if response.tool_calls else END
    )
tool_call = ToolNode(tools)    