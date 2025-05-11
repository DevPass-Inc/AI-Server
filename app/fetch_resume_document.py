from pymongo import MongoClient
from bson import ObjectId

MONGO_URL = "mongodb://devpass-mongo:27017"
client = MongoClient(MONGO_URL)
db = client['devpass']
resume_collection = db['resumes']

# 이력서 ID(Object)로 이력서 찾기
def fetch_resume_document(resume_id: str):
    return resume_collection.find_one({"_id": ObjectId(resume_id)})

# 이력서에서 유저 기술 스택 추출하기
def extract_user_stacks(resume: dict) -> list[str]:
    skills_section = resume.get("skills", [])
    stacks = set()

    for skill in skills_section:
        if isinstance(skill, dict):
            raw = skill.get("skill", "")
            if isinstance(raw, str) and raw.strip():
                stacks.add(raw.strip())

    return list(stacks)

# 기업추천에 사용할 텍스트 만들기
def convert_resume_to_text(resume: dict) -> str:
    parts = [f"요약: {' '.join(resume.get('summary', []))}"]

    for exp in resume.get("experience", []):
        parts.append(f"[프로젝트] {exp.get('project', '')} - {exp.get('summary', '')} ({exp.get('duration', '')})")
        parts.append(f"기술: {', '.join(exp.get('skills', []))}")
        parts.append(f"설명: {', '.join(exp.get('description', []))}")

    for act in resume.get("activities", []):
        parts.append(f"[활동] {act.get('title', '')} ({act.get('duration', '')}) - {act.get('description', '')}")

    return "\n".join(parts)