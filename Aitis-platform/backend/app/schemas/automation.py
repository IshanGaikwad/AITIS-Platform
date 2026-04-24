
from pydantic import BaseModel
from app.schemas.story import StoryCreate
from app.schemas.testcase import TestCaseOut

class AutomationRequest(BaseModel):
    story: StoryCreate
    test_case: TestCaseOut

class AutomationOut(BaseModel):
    id: str
    title: str
    framework: str
    language: str
    file_name: str
    content: str
