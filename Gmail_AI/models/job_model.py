from sqlmodel import Field, Column, Integer, Relationship
from Gmail_AI.models.JobFrameworkLink import JobFrameworkLink
from Gmail_AI.models.company_model import CompanyModel
from Gmail_AI.models.framework_model import FrameworkModel
from models.JobLanguageLink import JobLanguageLink
from models.JobSkillLink import JobSkillLink
from models.JobToolLink import JobToolLink
from models.base_model import BaseModel
from typing import Optional, List
from models.language_model import LanguageModel
from models.skill_model import SkillModel
from models.tool_model import ToolModel
from datetime import datetime, timezone
class JobModel(BaseModel, table=True):
    __tablename__ = "job"
    id : Optional[int] = Field(
    default = None,
    sa_column = Column(Integer,primary_key=True, autoincrement=True))
    job_id: str = Field(unique=True, index=True)
    job_name: str = Field(default="")
    job_description: str = Field(default = "", max_length=200)
    languages: Optional[List["LanguageModel"]] = Relationship(back_populates="jobs", link_model=JobLanguageLink)
    skills: Optional[List["SkillModel"]] = Relationship(
        back_populates="jobs", link_model=JobSkillLink
    )
    tools: Optional[List["ToolModel"]] = Relationship(back_populates="jobs", link_model=JobToolLink)
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    company: Optional["CompanyModel"] = Relationship(back_populates="jobs")
    frameworks: Optional[List["FrameworkModel"]] = Relationship(back_populates="jobs", link_model=JobFrameworkLink)
    apply_link: str = Field(default="")
    apply_status: str = Field(default="pending")
    apply_date: Optional[datetime] = Field(default_factory=None)
