from fastapi import FastAPI
from pydantic import BaseModel

from recommend_jobs import recommend_jobs_by_resume_id

app = FastAPI()


class RecommendationByResumeIdRequest(BaseModel):
    resumeId: str


@app.post("/recommend")
def recommend_by_resume_id(data: RecommendationByResumeIdRequest):
    recommendations = recommend_jobs_by_resume_id(data.resumeId)
    return recommendations
