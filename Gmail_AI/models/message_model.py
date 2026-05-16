from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship
from sqlalchemy import UniqueConstraint

from .base_model import BaseModel

if TYPE_CHECKING:
    from .user_model import UserModel


class MessageModel(BaseModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "thread_id", "message_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    message_id: str = Field(index=True)
    thread_id: str = Field(index=True)
    user_id: str = Field(foreign_key="user.user_id", index=True)

    sender: str
    subject: str
    date: datetime = datetime.now(timezone.utc).replace(tzinfo=None)
    content: str

    user: Optional["UserModel"] = Relationship(back_populates="unsolved_messages")