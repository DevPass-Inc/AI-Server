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