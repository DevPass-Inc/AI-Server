import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# MySQL 설정
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/devpass"

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Selenium 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)


def extract_number(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


# 회사 정보 저장 함수
def save_company(name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history):
    insert_company_query = text("""
        INSERT INTO companies (name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history)
        VALUES (:name, :category, :location, :avg_salary, :new_hire_avg_salary, :employee_count, :ceo_name, :company_history)
    """)

    session.execute(insert_company_query, {
        "name": name,
        "category": category,
        "location": location,
        "avg_salary": avg_salary,
        "new_hire_avg_salary": new_hire_avg_salary,
        "employee_count": employee_count,
        "ceo_name": ceo_name,
        "company_history": company_history,
    })

    session.commit()


# 회사 크롤링
start_id = 1
end_id = 50000

for company_id in range(start_id, end_id + 1):
    url = f"https://www.wanted.co.kr/company/{company_id}"
    try:
        driver.get(url)
        time.sleep(2)

        name = driver.find_element(By.CLASS_NAME, "wds-14f7cyg").text

        category_elements = driver.find_elements(By.CLASS_NAME, "wds-1h75osx")
        category = category_elements[0].text if len(category_elements) > 0 else None
        location = category_elements[1].text if len(category_elements) > 1 else None

        avg_salary_elements = driver.find_elements(By.CLASS_NAME, "wds-yh9s95")
        avg_salary = avg_salary_elements[0].text if len(avg_salary_elements) > 0 else None
        new_hire_avg_salary = avg_salary_elements[1].text if len(avg_salary_elements) > 1 else None

        employee_count = None
        try:
            employee_divs = driver.find_elements(By.CLASS_NAME, "ChartSummary_wrapper__xphdJ")
            for div in employee_divs:
                label = div.find_element(By.CLASS_NAME, "ChartSummary_wrapper__label__LFmFV").text
                if "인원" in label:
                    count_div = div.find_element(By.CLASS_NAME, "wds-yh9s95")
                    employee_count = extract_number(count_div.text)
                    break
        except Exception as e:
            print(f"⚠️ 직원 수 크롤링 실패: {e}")

        ceo_elements = driver.find_elements(By.CLASS_NAME, "CompanyInfoTable_definition__dd__oV9wp")
        ceo_name = ceo_elements[0].text if len(ceo_elements) > 0 else None
        company_history = ceo_elements[1].text if len(ceo_elements) > 1 else None

        save_company(name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name,
                     company_history)
        print(f"🎉 회사 정보 저장 완료: {company_id} - {name}")

    except Exception as e:
        print(f"⚠️ 회사 ID {company_id} 크롤링 실패: {e}")

driver.quit()
session.close()
