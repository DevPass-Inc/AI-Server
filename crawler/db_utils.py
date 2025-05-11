from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

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