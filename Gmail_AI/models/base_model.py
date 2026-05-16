from sqlmodel import Column, DateTime, Field, SQLModel
from datetime import datetime, timezone


class BaseModel(SQLModel):
    created_at: datetime = datetime.now(timezone.utc).replace(tzinfo=None)

    
    
    
    