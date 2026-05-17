from sqlmodel import Field, Column, Integer, Relationship
from models.base_model import BaseModel
from typing import Optional, List
from models.job_model import JobModel


class CompanyModel(BaseModel):
    __tablename__ = "company"
    id: Optional[int] = Field(
        default = None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )
    company_name: str = Field(default="", unique=True, index=True, max_length=200)
    jobs: Optional[List["JobModel"]] = Relationship(back_populates="company")
    
    