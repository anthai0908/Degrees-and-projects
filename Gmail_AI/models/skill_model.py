from sqlmodel import SQLModel, Field, Relationship, Column, Integer
from models.base_model import BaseModel
from typing import Optional, List

class SkillModel(BaseModel):
    __tablename__ = "skill"
    id: Optional[int] = Field(
        default = None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    skill_name: str = Field(default="", unique=True, index=True, max_length=200)
    