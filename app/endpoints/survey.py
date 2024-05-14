from fastapi import APIRouter, Response, status, HTTPException, Depends
from datetime import datetime, timedelta
from app.models.survey import SurveyAnswerSchema
from app.db.database import User
from app.services import utils
from app.core.config import settings
from app.serializers.userSerializers import userEntity, userResponseEntity
from app.services.utils import get_current_user_id
from app.services.survey_service import SurveyService, SurveyServiceException
from typing import List


router = APIRouter()

@router.get('/startSurvey')
def start_survey(surveyType :str ,userId: str = Depends(get_current_user_id)):
    try:
        result= SurveyService().startSurvey(surveyType,userId)
        return {"status": "success", "result": result}
    except SurveyServiceException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")  

@router.post('/{surveyId}')
def answerQuestions(payload: List[SurveyAnswerSchema], surveyId : str,userId: str = Depends(get_current_user_id)):
    
    try:
        result= SurveyService().collectAnswers(payload,surveyId,userId)
        return {"status": "success", "result": result}
    except SurveyServiceException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")  