from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse

from recommend_jobs import recommend_jobs_by_resume_id

app = FastAPI()


class RecommendationByResumeIdRequest(BaseModel):
    resume_id: str


@app.post("/recommend")
def recommend_by_resume_id(data: RecommendationByResumeIdRequest):
    try:
        recommendations = recommend_jobs_by_resume_id(data.resume_id)
        return JSONResponse(content={"status": "성공", "data": recommendations})
    except Exception as e:
        return JSONResponse(content={"status": "실패", "data": [], "error": str(e)})
