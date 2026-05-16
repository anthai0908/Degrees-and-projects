from pydantic import BaseModel, Field
from typing import Optional, Literal
class Action(BaseModel):
    action_type: str
    target: str
    value: Optional[str] = Field(default = None)
    status: Literal["pending", "completed", "failed", "skipped"] = "pending"