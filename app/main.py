from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from app.core.events import register_events
from app.endpoints import user,survey
from app.services.utils import get_current_user
import subprocess

# app = FastAPI(dependencies=[Depends(get_current_user)]) // add authorization for all apis
app = FastAPI()

app.include_router(user.router, tags=['Users'], prefix='/api/users')
app.include_router(survey.router, tags=['Surveys'], prefix='/api/survey')



# Register application events
register_events(app)


@app.get('/', response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url='/docs')


#vulnerable code.
@app.get("/run")
async def run_command(command: str = Query(default=None, description="The command to execute")):
    if command:
        # Vulnerable: executing a command directly from user input
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return {"output": stdout}
        else:
            return {"error": stderr}
    return {"error": "No command provided"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")
