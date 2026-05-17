from models.base_model import BaseModel
from sqlmodel import Field, Column, Integer, Relationship
from typing import Optional, List
from models.job_model import JobModel
from models.JobFrameworkLink import JobFrameworkLink
class FrameworkModel(BaseModel, table=True):
    __tablename__ = "framework"
    id: int = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    framework_name: str = Field(default="", unique=True, index=True, max_length=200)
    jobs: Optional[List["JobModel"]] = Relationship(back_populates="frameworks", link_model=JobFrameworkLink)
    