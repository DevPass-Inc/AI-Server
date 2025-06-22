from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

from app.fetch_resume_document import fetch_resume_document, convert_resume_to_text, extract_user_stacks

# DATABASE 설정
DATABASE_URL = "mysql+pymysql://user:password@devpass-db:3306/devpass"

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def fetch_job_postings():
    with Session() as session:
        try:
            query = text("""
                SELECT recruitment_id, company_name, position, main_task, qualification, preferred, benefit
                FROM recruitments
            """)
            result = session.execute(query).mappings().all()

            job_postings = []
            for row in result:
                description = " ".join(filter(None, [
                    row['main_task'], row['qualification'], row['preferred'],
                    row['benefit']
                ]))
                job_postings.append({
                    "recruitment_id": row['recruitment_id'],
                    "company_name": row['company_name'],
                    "position": row['position'],
                    "description": description
                })
            return job_postings
        except Exception as e:
            session.rollback()
            raise e

def calculate_tech_similarity(user_stacks, job_stacks):
    user_text = " ".join(user_stacks)
    job_text = " ".join(job_stacks)
    vectorizer = TfidfVectorizer(stop_words=None)
    vectors = vectorizer.fit_transform([user_text, job_text])
    return round(cosine_similarity(vectors[0], vectors[1])[0][0], 4)

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def calculate_context_similarity(user_resume, job_description):
    user_embedding = model.encode(user_resume, convert_to_tensor=True)
    job_embedding = model.encode(job_description, convert_to_tensor=True)
    return round(util.pytorch_cos_sim(user_embedding, job_embedding).item(), 4)

def calculate_final_score(tech_similarity, context_similarity, tech_weight=0.6, context_weight=0.4):
    return round((tech_weight * tech_similarity + context_weight * context_similarity) * 100, 2)

def recommend_jobs(user_stacks, user_resume):
    job_postings = fetch_job_postings()
    recommendations = []

    for job in job_postings:
        # 채용공고 관련 스택 조회
        try:
            job_tech_stacks_query = text("""
                SELECT s.name FROM recruitment_stacks rs
                JOIN stacks s ON rs.stack_id = s.stack_id
                WHERE rs.recruitment_id = :recruitment_id
            """)
            job_tech_stacks = [row['name'] for row in session.execute(job_tech_stacks_query, {
                "recruitment_id": job['recruitment_id']}).mappings().all()]
        except Exception as e:
            session.rollback()
            raise e

        tech_similarity = calculate_tech_similarity(user_stacks, job_tech_stacks)
        context_similarity = calculate_context_similarity(user_resume, job['description'])
        final_score = calculate_final_score(tech_similarity, context_similarity)

        tech_stack_status = [
            {
                "name": job_stack,
                "isRequired": str(any(job_stack.lower() == user_stack.lower() for user_stack in user_stacks)).lower()
            }
            for job_stack in job_tech_stacks
        ]

        recommendations.append({
            "recruitmentId": job['recruitment_id'],
            "companyName": job['company_name'],
            "position": job['position'],
            "finalScore": f"{final_score}%",
            "stacks": tech_stack_status
        })

    return sorted(recommendations, key=lambda x: float(x['finalScore'].strip('%')), reverse=True)[:2]

def recommend_jobs_by_resume_id(resume_id: str):
    # 1. 이력서 도큐먼트 조회
    doc = fetch_resume_document(resume_id)
    if not doc:
        raise ValueError("해당 resume_id에 대한 이력서를 찾을 수 없습니다.")

    resume = doc.get("resume")

    # 2. userStacks 추출
    user_stacks = extract_user_stacks(resume)

    # 3. userResume 텍스트 생성
    user_resume = convert_resume_to_text(resume)

    # 4. 추천 수행
    return recommend_jobs(user_stacks, user_resume)