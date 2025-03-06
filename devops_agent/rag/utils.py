from typing import List, Optional

from pydantic import BaseModel, model_validator


class RequestPayload(BaseModel):
    reset: Optional[bool] = True
    data_sources: Optional[List[str]] = None


class DataSource(BaseModel):
    instanceUrl: str
    user_email: str
    APIToken: str
    space: Optional[str] = None
    page_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def check_space_or_page_ids(self):
        if not self.space and not self.page_ids:
            raise ValueError(
                "Either 'space' or 'page_ids' must be provided in data_sources"
            )
        return self


class ConfluenceRequestPayload(BaseModel):
    reset: Optional[bool] = True
    data_sources: DataSource
