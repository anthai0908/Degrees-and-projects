from sqlmodel import Relationship, SQLModel, Field, Column, Integer
from typing import List, Optional
from Gmail_AI.models.job_model import JobModel
from models.base_model import BaseModel
from models.JobLanguageLink import JobLanguageLink

class LanguageModel(BaseModel):
    __tablename__ = "language"
    id: Optional[int] = Field(
        default = None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
        )
    language_name: str = Field(default="", unique=True, index=True, max_length=200)
    jobs: Optional[List["JobModel"]] = Relationship(back_populates="languages", link_model=JobLanguageLink)
    