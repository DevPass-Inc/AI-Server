import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from crawler.db_utils import fetch_additional_company_info
from crawler.es_utils import index_recruitment_to_elasticsearch
from crawler.utils import parse_career_range

DATABASE_URL = "mysql+pymysql://user:password@devpass-db:3306/devpass"

# MySQL 설정
def classify_position(position_name: str) -> str:
    keyword_map = {
        "Backend": ["서버", "백엔드", "backend", "API", "spring", "node", "django", "rails"],
        "Frontend": ["프론트", "프론트엔드", "frontend", "react", "vue", "angular"],
        "Data": ["데이터", "data", "분석"],
        "AI": ["AI", "ML", "딥러닝", "머신러닝"],
        "Mobile": ["android", "ios", "모바일", "앱", "swift", "kotlin"],
        "DevOps": ["인프라", "devops", "aws", "platform", "k8s", "docker", "클라우드"],
        "Security": ["보안", "security", "해킹", "취약점"],
        "QA": ["QA", "테스트", "test", "품질관리"],
        "PM": ["기획", "PM", "product manager", "PO", "기획자", "프로덕트 매니저"],
    }

    lowered = position_name.lower()
    for category, keywords in keyword_map.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return "ETC"

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
# options.add_argument('--headless=new')
# options.add_argument('--user-data-dir=/app/tmp/chrome-profile-recruit')

driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)

def fetch_stack_id_to_name():
    query = text("SELECT stack_id, name FROM stacks")
    result = session.execute(query).mappings().all()
    return {row["stack_id"]: row["name"] for row in result}


def fetch_stacks():
    query = text("SELECT stack_id, name FROM stacks")
    result = session.execute(query).mappings().all()
    return {str(row["name"]).lower(): row["stack_id"] for row in result}

def save_recruitment_with_tech(company_name, location, position_name, position, experience, due_date, image_url, details, tech_stacks):
    insert_recruitment_query = text("""
        INSERT INTO recruitments (company_name, location, position_name, position, career, deadline, image_url, main_task, qualification, preferred, benefit)
        VALUES (:company_name, :location, :position_name, :position, :career, :deadline, :image_url, :main_task, :qualification, :preferred, :benefit)
    """)

    session.execute(insert_recruitment_query, {
        "company_name": company_name,
        "location": location,
        "position_name": position_name,
        "position": position,
        "career": experience,
        "deadline": due_date,
        "image_url": image_url,
        "main_task": details[0] if len(details) > 0 else None,
        "qualification": details[1] if len(details) > 1 else None,
        "preferred": details[2] if len(details) > 2 else None,
        "benefit": details[3] if len(details) > 3 else None
    })

    session.commit()
    recruitment_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

    combined_text = " ".join(filter(None, details)).lower()

    matched_stack_ids = [
        tech_id for tech_name, tech_id in tech_stacks.items()
        if tech_name in combined_text
    ]

    if matched_stack_ids:
        for stack_id in matched_stack_ids:
            exists_query = text("""
                SELECT 1 FROM recruitment_stacks
                WHERE recruitment_id = :recruitment_id AND stack_id = :stack_id
            """)
            exists = session.execute(exists_query, {"recruitment_id": recruitment_id, "stack_id": stack_id}).fetchone()

            if not exists:
                session.execute(text("""
                    INSERT INTO recruitment_stacks (recruitment_id, stack_id)
                    VALUES (:recruitment_id, :stack_id)
                """), {"recruitment_id": recruitment_id, "stack_id": stack_id})

        session.commit()
        print(f"✅ 기술 스택 매핑 완료: {matched_stack_ids}")
    else:
        print("⚠️ 매핑된 기술 스택 없음.")

    company_info = fetch_additional_company_info(company_name)
    if not company_info:
        print(f"⚠️ 회사 정보 없음이지만 Elasticsearch에 기본값으로 인덱싱 진행")
        company_info = {
            "company_id": None,
            "category": "미상",
            "location": location,
            "avg_salary": None,
            "new_hire_avg_salary": None,
            "employee_count": None,
        }

    min_career, max_career = parse_career_range(experience)

    stack_id_to_name = fetch_stack_id_to_name()
    stacks = [
        {"id": stack_id, "name": stack_id_to_name.get(stack_id, "UNKNOWN")}
        for stack_id in matched_stack_ids
    ]

    index_recruitment_to_elasticsearch(
        recruitment_id,
        company_id=company_info["company_id"],
        company_name=company_name,
        position_name=position_name,
        position=position,
        location=location,
        career=experience,
        main_task=details[0] if len(details) > 0 else None,
        qualification=details[1] if len(details) > 1 else None,
        preferred=details[2] if len(details) > 2 else None,
        benefit=details[3] if len(details) > 3 else None,
        deadline=due_date,
        image_url=image_url,
        min_career=min_career,
        max_career=max_career,
        stack_ids=stack_ids,
        new_hire_avg_salary=company_info["new_hire_avg_salary"],
        employee_count=company_info["employee_count"]
    )

try:
    url = "https://www.wanted.co.kr/wdlist/518?country=kr&job_sort=job.recommend_order&years=-1&locations=all"
    driver.get(url)

    # 무한 스크롤 처리
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print("스크롤 완료, 모든 데이터를 로드했습니다.")

    tech_stacks = fetch_stacks()
    job_links = [card.get_attribute("href") for card in driver.find_elements(By.CSS_SELECTOR,
                                                                             ".JobCard_JobCard__Tb7pI a[data-attribute-id='position__click']")]

    print(f"총 {len(job_links)}개의 채용공고 링크 수집 완료.")

    for link in job_links:
        try:
            driver.get(link)

            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__WPrKC button"))
                )
                button.click()
                time.sleep(2)
            except Exception:
                pass

            company_name = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Link__NoBQI").text
            location = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__b9P4Y").text
            position_name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.wds-58fmok"))
            ).text
            position = classify_position(position_name)
            experience = driver.find_elements(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__b9P4Y")[
                -1].text
            min_career, max_career = parse_career_range(experience)
            due_date = driver.find_element(By.CSS_SELECTOR, ".JobDueTime_JobDueTime__yvhtg span").text

            try:
                image_element = driver.find_element(By.CSS_SELECTOR, ".JobCard_JobCard__thumb__iOtFn img")
                image_url = image_element.get_attribute("src")
            except Exception:
                image_url = None
                print("⚠️ 이미지 URL을 찾을 수 없음.")

            job_detail_wrapper = driver.find_element(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__WPrKC")
            paragraphs = job_detail_wrapper.find_elements(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__87w8I")
            details = [p.find_element(By.CSS_SELECTOR, "span").text.replace("\n", " ").strip() for p in paragraphs if p.text.strip()]

            save_recruitment_with_tech(company_name, location, position_name, position, experience, due_date, image_url, details, tech_stacks)
            print(f"🎉 채용공고 저장 완료: {company_name} - {position_name} ({position})")

        except Exception as e:
            print(f"❌ 에러 발생 ({link}): {e}")

finally:
    driver.quit()
    session.close()