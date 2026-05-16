
from sqlmodel import SQLModel, Field
from typing import Optional

class JobToolLink(SQLModel, table=True):
    __tablename__ = "job_tool_link"
    job_id: Optional[int] = Field(
        default=None,
        foreign_key="job.id", primary_key=True
        )
    tool_id: Optional[int] = Field(
        default=None,
        foreign_key="tool.id", primary_key=True
        )