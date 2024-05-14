from datetime import datetime
from pydantic import BaseModel, EmailStr, constr
from typing import Union


class SurveyAnswerSchema(BaseModel):
    questionId : str
    answer : int