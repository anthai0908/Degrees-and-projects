from sqlmodel import Field, Column, Integer
from models.base_model import BaseModel
from typing import Optional, List
from models.job_model import JobModel
from models.skill_model import SkillModel

class JobSkillLink(BaseModel, table=True):  
    __tablename__="job_skill_link"
    job_id: Optional[int] = Field(
        default=None,
        foreign_key="job.id", primary_key=True
        )
    skill_id: Optional[int] = Field(
        default=None,
        foreign_key="skill.id", primary_key=True
        )