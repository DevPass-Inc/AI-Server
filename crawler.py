import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# MySQL 설정
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/devpass"

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Selenium 설정
options = webdriver.ChromeOptions()
# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(options=options)


def fetch_stacks():
    query = text("SELECT stack_id, name FROM stack")
    result = session.execute(query).mappings().all()
    return {row['name'].lower(): row['stack_id'] for row in result}


# 채용공고 저장 및 매핑 함수
def save_recruitment_with_tech(company_name, location, position, experience, due_date, details, tech_stacks):
    # 채용공고 삽입
    insert_recruitment_query = text("""
        INSERT INTO recruitment (company_name, location, position, career, deadline, main_task, qualification, preferred, benefit, recruiting)
        VALUES (:company_name, :location, :position, :career, :deadline, :main_task, :qualification, :preferred, :benefit, :recruiting)
    """)

    session.execute(insert_recruitment_query, {
        "company_name": company_name,
        "location": location,
        "position": position,
        "career": experience,
        "deadline": due_date,
        "main_task": details[0] if len(details) > 0 else None,
        "qualification": details[1] if len(details) > 1 else None,
        "preferred": details[2] if len(details) > 2 else None,
        "benefit": details[3] if len(details) > 3 else None,
        "recruiting": details[4] if len(details) > 4 else None
    })

    session.commit()

    # 방금 삽입된 채용공고 ID 가져오기
    recruitment_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

    # 기술 스택 매핑
    combined_text = " ".join(filter(None, details)).lower()
    matched_stack_ids = [tech_id for tech_name, tech_id in tech_stacks.items() if tech_name in combined_text]

    if matched_stack_ids:
        for stack_id in matched_stack_ids:
            # 중복 여부 확인 쿼리
            exists_query = text("""
                    SELECT 1 FROM recruitment_stack
                    WHERE recruitment_id = :recruitment_id AND stack_id = :stack_id
                """)
            exists = session.execute(exists_query, {"recruitment_id": recruitment_id, "stack_id": stack_id}).fetchone()

            if not exists:  # 중복이 아닐 때만 삽입
                session.execute(text("""
                        INSERT INTO recruitment_stack (recruitment_id, stack_id)
                        VALUES (:recruitment_id, :stack_id)
                    """), {"recruitment_id": recruitment_id, "stack_id": stack_id})

        session.commit()
        print(f"기술 스택 매핑 완료: {matched_stack_ids}")
    else:
        print("매핑된 기술 스택 없음.")
try:
    url = "https://www.wanted.co.kr/wdlist/518?country=kr&job_sort=job.recommend_order&years=-1&locations=all"
    driver.get(url)

    # # 무한 스크롤 처리
    # SCROLL_PAUSE_TIME = 2
    # last_height = driver.execute_script("return document.body.scrollHeight")
    #
    # while True:
    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #     time.sleep(SCROLL_PAUSE_TIME)
    #     new_height = driver.execute_script("return document.body.scrollHeight")
    #     if new_height == last_height:
    #         break
    #     last_height = new_height
    #
    # print("스크롤 완료, 모든 데이터를 로드했습니다.")
    # 무한 스크롤 처리 (최대 10개 제한)
    SCROLL_PAUSE_TIME = 2
    MAX_JOBS = 10

    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 현재 채용공고 수 확인
        job_cards = driver.find_elements(By.CSS_SELECTOR,
                                         ".JobCard_JobCard__Tb7pI a[data-attribute-id='position__click']")

        # 100개 이상 수집 시 스크롤 중단
        if len(job_cards) >= MAX_JOBS:
            print(f"10개의 채용공고를 수집하여 스크롤을 중단합니다. 현재 수집된 공고 수: {len(job_cards)}")
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("페이지 끝에 도달하여 스크롤을 중단합니다.")
            break
        last_height = new_height

    print("스크롤 완료, 모든 데이터를 로드했습니다.")

    # 기술 스택 가져오기
    tech_stacks = fetch_stacks()

    job_links = [card.get_attribute("href") for card in driver.find_elements(By.CSS_SELECTOR, ".JobCard_JobCard__Tb7pI a[data-attribute-id='position__click']")]
    print(f"총 {len(job_links)}개의 채용공고가 있습니다.")

    for link in job_links:
        try:
            driver.get(link)

            # '더 보기' 버튼 클릭 시도
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__G4CNd button"))
                )
                button.click()
                time.sleep(2)
            except Exception:
                pass  # 버튼이 없으면 그냥 진행

            company_name = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Link__zAvYv").text
            location = driver.find_element(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__yT4OD").text
            position_name = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.wds-jtr30u"))).text
            experience = driver.find_elements(By.CSS_SELECTOR, ".JobHeader_JobHeader__Tools__Company__Info__yT4OD")[-1].text
            due_date = driver.find_element(By.CSS_SELECTOR, ".JobDueTime_JobDueTime__3yzxa span").text

            job_detail_wrapper = driver.find_element(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__wrapper__G4CNd")
            paragraphs = job_detail_wrapper.find_elements(By.CSS_SELECTOR, ".JobDescription_JobDescription__paragraph__Lhegj")

            details = []
            for paragraph in paragraphs:
                try:
                    content = paragraph.find_element(By.CSS_SELECTOR, "span").text.replace("\n", " ").lstrip("• ").strip()
                    details.append(content)
                except Exception:
                    continue

            save_recruitment_with_tech(company_name, location, position_name, experience, due_date, details, tech_stacks)
            print(f"채용 공고 및 기술 스택 저장 완료: {company_name}, {position_name}")

        except Exception as e:
            print(f"에러 발생 ({link}): {e}")

finally:
    driver.quit()
    session.close()