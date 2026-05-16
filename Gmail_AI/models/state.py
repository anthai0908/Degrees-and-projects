from pydantic import BaseModel, Field
from typing import Annotated, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import json
from typing import Optional


class graphState(BaseModel):
    user_id: str
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    long_term_memory: str = ""
    login_password: Optional[str] = None
    
class jobScrapingState(BaseModel):
    user_id: str
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    long_tem_memory: str = "" ### use to get procedural memory from mem0
    current_observation: str = "" ### use to get current observation
    application_preferences: str = "" ### use to get user preference
    execution_summary: dict[str, Any] = Field(
        default_factory=lambda: {
            "steps": []
        }
    )
    saved_job_id_lists: List[str] = Field(default_factory=list) ### List of saved job_id not applied yet
    number_of_new_jobs_scraped: int = 0
    
    
class JobApplicationGraphState(BaseModel):
    user_id: str
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    registration_info: dict[str, Any] = Field(default_factory=dict) ###Use when registering required
    long_term_memory: str = "" ###To get all memory relating to user as well as procedures for job application
    current_observation: str = "" ###To get all observation of the current page
    execution_summary: dict[str, Any] = Field(
        default_factory=lambda: {
            "steps": [],
        }
    ) ###Use when to execute plan accordingly, and for comparison with results, errors
    
