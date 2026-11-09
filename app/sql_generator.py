import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.schema import get_database_schema
from app.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

model_name = os.getenv("GEMINI_MODEL")

if not model_name:
    raise ValueError("GEMINI_MODEL is missing from .env")

llm = ChatGoogleGenerativeAI(
    model=model_name,
    temperature=0,
    max_retries=2,
)


def generate_sql(question: str) -> str:
    logger.info("SQL generation started")

    try:
        schema = get_database_schema()

        prompt = f"""
    You are a PostgreSQL SQL query generator.
    
    Generate one SQL query that answers the user's question.
    
    Rules:
    - Use only tables and columns in the supplied schema.
    - Generate exactly one read-only SELECT query.
    - Do not generate INSERT, UPDATE, DELETE, DROP, ALTER,
      CREATE, or other data-modifying statements.
    - Do not invent table names or column names.
    - Use the correct foreign-key relationships for joins.
    - Return SQL only, without Markdown fences or explanations.
    - If the question cannot be answered using the schema,
      explain that the schema is insufficient instead of
      inventing a query.
    
    Database schema:
    {schema}
    
    User question:
    {question}
    """

        response = llm.invoke(prompt)
        logger.info(f"response: {response}") # shd not do this in prod (since, huge response -> huge logs, can contain sensitive data) so, look for alternatives
        content = response.content
        logger.info(f"content: {content}")
        logger.info(f"content type: {type(content)}")

        # if not isinstance(content, str):
        #     raise ValueError("Expected a text response from Gemini")

        logger.info("SQL generation completed successfully")
        return content

    except Exception:
        logger.exception("SQL generation failed")
        raise


if __name__ == "__main__":
    question = input("Ask a question about the database: ")
    sql = generate_sql(question)

    print("\nGenerated SQL:")
    print(sql)