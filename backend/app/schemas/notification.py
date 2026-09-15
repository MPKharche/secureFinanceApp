import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    title: str
    message: str
    metadata: dict
    read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
