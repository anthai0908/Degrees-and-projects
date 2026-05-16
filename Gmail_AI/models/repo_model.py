from sqlmodel import Field, Column, Integer, Relationship
from models.base_model import BaseModel
from typing import Optional
from datetime import datetime, timezone

class RepoModel(BaseModel):
    __tablename__ = "job"
    id : Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    repo_name: str = Field(default="", index=True, unique=True)
    last_processed_commit: str = Field(default="")
    last_processed_commit_time: datetime = Field(default_factory=datetime.now(timezone.utc))

    