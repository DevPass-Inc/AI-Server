from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from recommend_jobs import recommend_jobs

app = FastAPI()

class RecommendationRequest(BaseModel):
    user_stacks: List[str]
    user_resume: str

@app.post("/recommend")
def recommend_endpoint(data: RecommendationRequest):
    recommendations = recommend_jobs(data.user_stacks, data.user_resume)
    return {"recommendations": recommendations}