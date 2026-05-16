from sqlmodel import Field, Column, Integer, Relationship
from models.base_model import BaseModel
from typing import Optional, List
from models.job_model import JobModel
from models.language_model import LanguageModel

class JobLanguageLink(BaseModel, table=True):
    __tablename__ = "job_language_link"
    job_id: Optional[int] = Field(
        default=None,
        foreign_key="job.id", primary_key=True
    )
    language_id: Optional[int] = Field(
        default=None,
        foreign_key="language.id", primary_key=True
    )