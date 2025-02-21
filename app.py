from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from recommend_jobs import recommend_jobs

app = FastAPI()


class RecommendationRequest(BaseModel):
    userStacks: List[str]
    userResume: str


@app.post("/recommend")
def recommend_endpoint(data: RecommendationRequest):
    recommendations = recommend_jobs(data.userStacks, data.userResume)
    return recommendations
