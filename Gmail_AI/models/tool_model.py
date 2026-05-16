from sqlmodel import Field, Column, Integer, Relationship
from typing import Optional, List
from models.JobToolLink import JobToolLink
from models.base_model import BaseModel
from sqlalchemy import Column, Integer
from models.job_model import JobModel
class ToolModel(BaseModel):
    __tablename__ = 'tool'
    id: Optional[Integer] = Field(
        default = None,
        sa_column = Column(Integer, primary_key= True, autoincrement=True)
    )
    tool_name: str = Field(default ="", max_length = 50)
    jobs: Optional[List[JobModel]] = Relationship(
        back_populates="tools", link_model=JobToolLink  
    )  