from pydantic import BaseModel


class Channels(BaseModel):
    channel_id: int
    url: str
    name: str

