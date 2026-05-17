from sqlmodel import SQLModel, Field, Relationship, Column, Integer
from Gmail_AI.models.job_model import JobModel
from models.base_model import BaseModel
from typing import Optional, List
from models.JobSkillLink import JobSkillLink
class SkillModel(BaseModel):
    __tablename__ = "skill"
    id: Optional[int] = Field(
        default = None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    skill_name: str = Field(default="", unique=True, index=True, max_length=200)
    jobs: Optional[List["JobModel"]] = Relationship(back_populates="skills", link_model=JobSkillLink)