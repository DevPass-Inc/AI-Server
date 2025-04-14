from fastapi import FastAPI
from pydantic import BaseModel

from recommend_jobs import recommend_jobs_by_resume_id

app = FastAPI()


class RecommendationByResumeIdRequest(BaseModel):
    resumeId: str


@app.post("/recommend")
def recommend_by_resume_id(data: RecommendationByResumeIdRequest):
    try:
        recommendations = recommend_jobs_by_resume_id(data.resumeId)
        return {"status": "성공", "data": recommendations}
    except Exception as e:
        return {"status": "에러", "message": str(e)}
