"""Request models."""
from pydantic import BaseModel


class GithubRequest(BaseModel):
    url: str
