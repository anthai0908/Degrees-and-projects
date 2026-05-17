from sqlmodel import Field, Column, Integer, Relationship
from models.base_model import BaseModel
from typing import Optional, List
from models.job_model import JobModel
from models.framework_model import FrameworkModel

class JobFrameworkLink(BaseModel, table=True):
    __tablename__ = "job_framework_link"
    job_id: Optional[int] = Field(default=None, primary_key=True, foreign_key="job.id")
    framework_id: Optional[int] = Field(default=None, primary_key=True, foreign_key="framework.id")