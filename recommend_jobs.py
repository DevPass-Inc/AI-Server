from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

# DATABASE 설정
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/devpass"

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

def fetch_job_postings():
    query = text("""
        SELECT recruitment_id, company_name, position, main_task, qualification, preferred, benefit, recruiting
        FROM recruitment
    """)
    result = session.execute(query).mappings().all()

    job_postings = []
    for row in result:
        description = " ".join(filter(None, [
            row['main_task'], row['qualification'], row['preferred'],
            row['benefit'], row['recruiting']
        ]))
        job_postings.append({
            "recruitment_id": row['recruitment_id'],
            "company_name": row['company_name'],
            "position": row['position'],
            "description": description
        })
    return job_postings

def calculate_tech_similarity(user_stacks, job_stacks):
    user_text = " ".join(user_stacks)
    job_text = " ".join(job_stacks)
    vectorizer = TfidfVectorizer()
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
        job_tech_stacks_query = text("""
            SELECT s.name FROM recruitment_stack rs
            JOIN stack s ON rs.stack_id = s.stack_id
            WHERE rs.recruitment_id = :recruitment_id
        """)
        job_tech_stacks = [row['name'] for row in session.execute(job_tech_stacks_query, {
            "recruitment_id": job['recruitment_id']}).mappings().all()]

        # 기술 유사도 계산
        tech_similarity = calculate_tech_similarity(user_stacks, job_tech_stacks)

        # 문맥 유사도 계산
        context_similarity = calculate_context_similarity(user_resume, job['description'])

        # 최종 점수 계산
        final_score = calculate_final_score(tech_similarity, context_similarity)

        # 사용자 스택 상태 표시
        tech_stack_status = [
            {"stack": stack, "isRequired": stack.lower() in [js.lower() for js in job_tech_stacks]}
            for stack in user_stacks
        ]

        recommendations.append({
            "company_name": job['company_name'],
            "position": job['position'],
            "final_score": f"{final_score}%",
            "tech_stacks": tech_stack_status
        })

    return sorted(recommendations, key=lambda x: float(x['final_score'].strip('%')), reverse=True)[:2]