from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from app.core.events import register_events
from app.endpoints import user,survey
from app.services.utils import get_current_user

# app = FastAPI(dependencies=[Depends(get_current_user)]) // add authorization for all apis
app = FastAPI()

app.include_router(user.router, tags=['Users'], prefix='/api/users')
app.include_router(survey.router, tags=['Surveys'], prefix='/api/survey')



# Register application events
register_events(app)


@app.get('/', response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url='/docs')


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")
