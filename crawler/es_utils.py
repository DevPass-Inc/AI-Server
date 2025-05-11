from elasticsearch import Elasticsearch

es = Elasticsearch(
    "http://devpass-elasticsearch:9200",
    headers={
        "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
        "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
    }
)

def index_company_to_elasticsearch(company_id, name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history):
    doc = {
        "id": company_id,
        "name": name,
        "category": category,
        "location": location,
        "avgSalary": avg_salary,
        "newHireAvgSalary": new_hire_avg_salary,
        "employeeCount": employee_count,
        "ceoName": ceo_name,
        "companyHistory": company_history,
    }
    es.index(index="companies", id=company_id, document=doc)

def index_recruitment_to_elasticsearch(
    recruitment_id, company_name, position_name, position, location, career,
    main_task, qualification, preferred, benefit, deadline, image_url,
    min_career, max_career
):
    doc = {
        "id": recruitment_id,
        "companyName": company_name,
        "positionName": position_name,
        "position": position,
        "location": location,
        "career": career,
        "mainTask": main_task,
        "qualification": qualification,
        "preferred": preferred,
        "benefit": benefit,
        "deadline": deadline,
        "imageUrl": image_url,
        "minCareer": min_career,
        "maxCareer": max_career,
    }

    es.index(index="recruitments", id=recruitment_id, document=doc)