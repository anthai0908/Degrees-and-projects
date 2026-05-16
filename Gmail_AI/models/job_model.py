from sqlmodel import Field, Column, Integer, Relationship
from models.JobLanguageLink import JobLanguageLink
from models.JobSkillLink import JobSkillLink
from models.JobToolLink import JobToolLink
from models.base_model import BaseModel
from typing import Optional, List
from models.language_model import LanguageModel
from models.skill_model import SkillModel
from models.tool_model import ToolModel
from datetime import datetime, timezone
class JobModel(BaseModel):
    __tablename__ = "job"
    id : Optional[int] = Field(
    deault = None,
    sa_column = Column(Integer,primary_key=True, autoincrement=True))
    job_id: str = Field(primary_key=True, unique=True, index=True)
    job_name: str = Field(default="")
    job_description: str = Field(default = "", max_length=200)
    languages: Optional[List["LanguageModel"]] = Relationship(back_populates="language", link_model=JobLanguageLink)
    skills: Optional[List["SkillModel"]] = Relationship(
        back_populates="job", link_model=JobSkillLink
    )
    tools: Optional[List["ToolModel"]] = Relationship(back_populates="job", link_model=JobToolLink)
    company_id: str = Field(foreign_key="company.id")
    apply_link: str = Field(default="")
    apply_status: str = Field(default="pending")
    apply_date: datetime = datetime.now(timezone.utc).replace(tzinfo=None)
