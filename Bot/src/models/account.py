from pydantic import BaseModel


class Account(BaseModel):
    login: str
    password: str
    access_token: str
    last_used_time: int
