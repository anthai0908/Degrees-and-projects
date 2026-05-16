from pydantic import BaseModel
from typing import Optional
class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: Optional[str] = None
    caption: Optional[str] = None
    
    @property
    def content(self):
        return self.text or self.caption or "".strip()
    
class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None   
