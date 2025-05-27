import re
import sys
import time
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from crawler.es_utils import index_company_to_elasticsearch

# MySQL 설정
DATABASE_URL = "mysql+pymysql://user:password@devpass-db:3306/devpass"

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Selenium 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.binary_location = "/usr/bin/chromium"
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
# options.add_argument('--user-data-dir=/app/tmp/chrome-profile-company')
# options.add_argument('--headless=new')

driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)


def extract_number(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


# 회사 정보 저장 함수
def save_company(name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history):
    insert_company_query = text("""
        INSERT INTO companies (name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history)
        VALUES (:name, :category, :location, :avg_salary, :new_hire_avg_salary, :employee_count, :ceo_name, :company_history)
    """)

    result = session.execute(insert_company_query, {
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

    company_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    index_company_to_elasticsearch(company_id, name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name, company_history)


# 회사 크롤링
start_id = 1
end_id = 10

for company_id in range(start_id, end_id + 1):
    url = f"https://www.wanted.co.kr/company/{company_id}"
    try:
        driver.get(url)
        time.sleep(2)

        try:
            name_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "wds-1f8kxw2"))
            )
            name = name_element.text
        except TimeoutException:
            print(f"⚠️ 회사 ID {company_id} 크롤링 실패: 이름 요소를 찾을 수 없음")
            continue

        category_elements = driver.find_elements(By.CLASS_NAME, "wds-ilos43")
        category = category_elements[0].text if len(category_elements) > 0 else None
        location = category_elements[1].text if len(category_elements) > 1 else None

        avg_salary_elements = driver.find_elements(By.CLASS_NAME, "wds-u1e2rb")
        avg_salary = avg_salary_elements[0].text if len(avg_salary_elements) > 0 else None
        new_hire_avg_salary = avg_salary_elements[1].text if len(avg_salary_elements) > 1 else None

        employee_count = None
        try:
            employee_divs = driver.find_elements(By.CLASS_NAME, "ChartSummary_wrapper__xphdJ")
            for div in employee_divs:
                label = div.find_element(By.CLASS_NAME, "ChartSummary_wrapper__label__LFmFV").text
                if "인원" in label:
                    count_div = div.find_element(By.CLASS_NAME, "wds-u1e2rb")
                    employee_count = extract_number(count_div.text)
                    break
        except Exception as e:
            print(f"⚠️ 직원 수 크롤링 실패: {e}")

        ceo_name = None
        company_history = None

        try:
            dt_elements = driver.find_elements(By.CLASS_NAME, "CompanyInfoTable_definition__dt__hMyz7")
            dd_elements = driver.find_elements(By.CLASS_NAME, "CompanyInfoTable_definition__dd__oV9wp")

            for dt, dd in zip(dt_elements, dd_elements):
                label = dt.text.strip()
                if label == "대표자명":
                    ceo_name = dd.text.strip()
                elif label == "연혁":
                    company_history = dd.text.strip()

        except Exception as e:
            print(f"⚠️ 대표자명 및 연혁 크롤링 실패: {e}")

        save_company(name, category, location, avg_salary, new_hire_avg_salary, employee_count, ceo_name,
                     company_history)
        print(f"🎉 회사 정보 저장 완료: {company_id} - {name}")

    except Exception as e:
        print(f"⚠️ 회사 ID {company_id} 크롤링 실패: {e}")

driver.quit()
session.close()
sys.exit(0)