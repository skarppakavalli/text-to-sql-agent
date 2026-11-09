import sqlglot
from sqlglot import exp # Contains SQL expression classes that represent different SQL constructs
from sqlglot.errors import ParseError #raises exception when SQLGlot cannot parse the gn exp
from sqlglot.optimizer.scope import traverse_scope # to traverse CTE & sub-queries

from sqlalchemy import inspect
from app.schema import engine
from app.logger import get_logger

logger = get_logger(__name__)

ALLOWED_SCHEMA = "public"

def get_allowed_tables() -> set[str]:
    inspector = inspect(engine) #Creates an SQLAlchemy inspector to retrieve DB metadata.

    return set(inspector.get_table_names(schema= ALLOWED_SCHEMA)) #Gets the table names from the PostgreSQL public schema.

def validate_tables_by_scope(tree: exp.Expression) -> tuple[bool, str]:
    allowed_tables = get_allowed_tables()

    for scope in traverse_scope(tree):
        for source in scope.sources.values():

            if isinstance(source, exp.Table):
                table_name = source.name.lower()
                schema_name = source.db.lower()
                catalog_name = source.catalog.lower()

                if catalog_name:
                    return False, "Cross-database access is not allowed."

                if schema_name and schema_name != ALLOWED_SCHEMA:
                    return False, f"Access to schema '{schema_name}' is not allowed."

                if table_name not in allowed_tables:
                    return False, f"Table '{table_name}' is not allowed."

    return True, "All physical table references are allowed."

def validate_table_names(tree: exp.Expression) -> tuple[bool, str]:
    allowed_tables = get_allowed_tables()

    for scope in traverse_scope(tree):
        for source in scope.sources.values():

            if isinstance(source, exp.Table): # scope will be table only for actual table names (not for tables created during CTE). CTE and derived-query sources are represented by 'Scope' objects (Not by 'Table' objects). ('Scope' & 'Table' -> types in sqlglot)
                table_name = source.name.lower()
                schema_name = source.db.lower()
                catalog_name = source.catalog.lower()

                if catalog_name:
                    return False, "Cross-database access is not allowed."

                if schema_name and schema_name != ALLOWED_SCHEMA:
                    return False, f"Access to schema '{schema_name}' is not allowed."

                if table_name not in allowed_tables:
                    return False, f"Table '{table_name}' is not allowed."

    return True, "All physical table references are allowed."


def validate_sql(sql: str) -> tuple[bool, str]: #why tuple (& not list)? since, tuple is immutable (llm & any other code cant modify)
    logger.info("SQL validation started")
    try:
        statements = []
        for statement in sqlglot.parse(sql, read= "postgres"):
            if statement is not None:
                if isinstance(statement, exp.Query): # exp.Query => allows SELECT & UNION (b/ r read-only queries)
                    statements.append(statement)
                else:
                    logger.warning("SQL validation rejected: non-query statement")
                    return False, "Read-Only statements are allowed."

    except ParseError:
        logger.warning("SQL validation rejected: invalid SQL syntax")
        return False, "Invalid SQL syntax."

    if len(statements) != 1:
        logger.warning(
            "SQL validation rejected: expected one statement, got %d",
            len(statements),
        )
        return False, "Only 1 statement is allowed" #we are allowing only 1 query, eventhough multiple read-only queries are not harmful, for now, we are limiting to 1 to avoid unnecessary select queries

    '''
    A query can have a SELECT at the top level but still contain a data-modifying operation inside a CTE(Common Table Expression)/ subquery. exp.Query only checks the root level query, so, these will not be found by that if condition.
    Example:
        WITH deleted_customers AS (
            DELETE FROM customer
            WHERE country = 'India'
            RETURNING *
        )
        SELECT * FROM deleted_customers;
    So, we are getting the AST & traversing it to not allow these type of queries.
    Note: 
    - We are allowing CTE & sub-queries which don't have data modifying statements (i.e:- we are forbidding CTEs & sub-queries completely).
    - AST validation checks the parsed meaning of SQL, not just the keywords appearing in the SQL text.
    '''

    tree = statements[0]
    forbidden_nodes = (
        exp.DML, # INSERT, UPDATE, DELETE, MERGE
        exp.DDL, # CREATE, DROP, ALTER
        exp.Command, # Special or unsupported SQL commands
        exp.Into, # SELECT INTO, which can create a table
        exp.Lock # Locking operations: SELECT ... FOR UPDATE (This kind of SQL selects the row and locks them for later updation. Eventhough this has "UPDATE" it won't be caught by DML as AST checks the meaning of the SQL not the k/w).
    )
    for node in tree.walk():
        if isinstance(node, forbidden_nodes):
            logger.warning(
                "SQL validation rejected: forbidden operation %s",
                type(node).__name__,
            )
            return False, f"SQL Operation not allowed: {type(node).__name__}"


    is_valid_table, table_message = validate_table_names(tree)
    if not is_valid_table:
        logger.warning("SQL validation rejected: %s", table_message)
        return is_valid_table, table_message

    '''
    Note:
        SELECT pg_sleep(100);
    This is technically a SELECT query and doesn't contain a DML or DDL operation, but it can consume database resources.
    Similarly, some database functions can have side effects. (which are not found by our code).
    We'll address this through PostgreSQL permissions, transaction settings, statement timeouts and result limits.
    '''

    logger.info("SQL validation passed")
    return True, "SQL passed basic validation."

if __name__ == "__main__":
    if __name__ == "__main__":
        test_queries = [
            "SELECT * FROM customer",
            "DELETE FROM customer",
            "SELECT * FROM employees",
        ]

        for query in test_queries:
            is_valid, message = validate_sql(query)
            print(f"\nQuery: {query}")
            print(f"Valid: {is_valid}")
            print(f"Message: {message}")
