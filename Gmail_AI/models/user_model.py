
from typing import List, Optional, TYPE_CHECKING
from pydantic import EmailStr
from models.base_model import BaseModel, Field
from sqlmodel import Relationship
from sqlalchemy import Column, Integer



if TYPE_CHECKING:
    from message_model import MessageModel


class UserModel(BaseModel, table=True):
    __tablename__ = "user"
    
    id: Optional[int] = Field(
    default=None,
    sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )

    user_id: str = Field(unique=True, index=True, primary_key=True)

    e_mail: EmailStr = Field(unique=True, index=True)

    unsolved_messages: List["MessageModel"] = Relationship(back_populates="user")
    
    encrypted_refresh_token : str = Field(default="")
    
    hashed_password : str = Field(default="")