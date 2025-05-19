from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import re

DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/devpass"
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

def fetch_stack_ids_by_recruitment_id(recruitment_id: int) -> list[int]:
    result = session.execute(text("""
        SELECT stack_id
        FROM recruitment_stacks
        WHERE recruitment_id = :recruitment_id
    """), {"recruitment_id": recruitment_id}).fetchall()
    return [row[0] for row in result]

def extract_number(text):
    match = re.search(r"\d+", text.replace(",", ""))
    return int(match.group()) if match else None

def fetch_additional_company_info(company_name: str):
    result = session.execute(text("""
        SELECT id, category, location, avg_salary, new_hire_avg_salary, employee_count
        FROM companies
        WHERE name = :company_name
    """), {"company_name": company_name}).mappings().first()

    if not result:
        raise Exception(f"회사 정보 없음: {company_name}")

    return {
        "company_id": result["id"],
        "category": result["category"],
        "location": result["location"],
        "avg_salary": result["avg_salary"],
        "new_hire_avg_salary": result["new_hire_avg_salary"],
        "employee_count": result["employee_count"],
    }