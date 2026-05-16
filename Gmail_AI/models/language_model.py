from sqlmodel import SQLModel, Field, Column, Integer
from typing import Optional
from models.base_model import BaseModel


class LanguageModel(BaseModel):
    __tablename__ = "language"
    id: Optional[int] = Field(
        default = None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
        )
    language_name: str = Field(default="", unique=True, index=True, max_length=200)