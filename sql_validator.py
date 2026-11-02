import sqlglot
from sqlglot import exp # Contains SQL expression classes that represent different SQL constructs
from sqlglot.errors import ParseError #raises exception when SQLGlot cannot parse the gn exp
from sqlglot.optimizer.scope import traverse_scope # to traverse CTE & sub-queries

from sqlalchemy import inspect
from schema import engine

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
    try:
        statements = []
        for statement in sqlglot.parse(sql, read= "postgres"):
            if statement is not None:
                if isinstance(statement, exp.Query): # exp.Query => allows SELECT & UNION (b/ r read-only queries)
                    statements.append(statement)
                else:
                    return False, "Read-Only statements are allowed."

    except ParseError:
        return False, "Invalid SQL syntax."

    if len(statements) != 1:
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
            return False, f"SQL Operation not allowed: {type(node).__name__}"


    is_valid_table, table_message = validate_table_names(tree)
    if not is_valid_table:
        return is_valid_table, table_message

    '''
    Note:
        SELECT pg_sleep(100);
    This is technically a SELECT query and doesn't contain a DML or DDL operation, but it can consume database resources.
    Similarly, some database functions can have side effects. (which are not found by our code).
    We'll address this through PostgreSQL permissions, transaction settings, statement timeouts and result limits.
    '''

    return True, "SQL passed basic validation."

if __name__ == "__main__":
    test_cases = [
        # Valid queries
        ("Basic SELECT", "SELECT * FROM customer;"),
        ("WHERE", "SELECT name, city FROM customer WHERE country = 'India';"),
        (
            "JOIN",
            """SELECT c.first_name, i.total
               FROM customer c
               JOIN invoice i ON c.customer_id = i.customer_id;"""
        ),
        ("LIMIT OFFSET", "SELECT * FROM customer LIMIT 5 OFFSET 2;"),
        (
            "GROUP BY HAVING",
            """SELECT country, COUNT(*)
               FROM customer
               GROUP BY country
               HAVING COUNT(*) > 5;"""
        ),
        (
            "Subquery",
            """SELECT * FROM customer
               WHERE customer_id IN (
                   SELECT customer_id FROM invoice
               );"""
        ),
        (
            "UNION",
            """SELECT artist_id FROM album
               UNION
               SELECT artist_id FROM album WHERE artist_id = 1;"""
        ),
        (
            "CTE",
            """WITH customer_sales AS (
                   SELECT customer_id, SUM(total) AS amount
                   FROM invoice GROUP BY customer_id
               )
               SELECT * FROM customer_sales;"""
        ),

        # Invalid queries
        ("DELETE", "DELETE FROM customer WHERE customer_id = 1;"),
        ("UPDATE", "UPDATE customer SET city = 'Chennai';"),
        ("DROP", "DROP TABLE customer;"),
        ("SELECT INTO", "SELECT * INTO customer_backup FROM customer;"),
        ("Unknown table", "SELECT * FROM employees;"),
        ("Unknown schema table", "SELECT * FROM public.employees;"),
        ("Disallowed schema", "SELECT * FROM private.customer;"),
        (
            "Multiple statements",
            "SELECT * FROM customer; SELECT * FROM invoice;"
        ),
        ("Invalid syntax", "SELEC * FROM customer;"),
        (
            "Nested DML",
            """WITH x AS (
                   DELETE FROM customer RETURNING *
               )
               SELECT * FROM x;"""
        ),

        # Edge cases
        (
            "CTE name matches physical table",
            """WITH customer AS (SELECT * FROM invoice)
               SELECT * FROM customer;"""
        ),
        ("Schema-qualified allowed table", "SELECT * FROM public.customer;"),
        (
            "External catalog",
            "SELECT * FROM otherdb.public.customer;"
        ),
        ("Row locking", "SELECT * FROM customer FOR UPDATE;"),
    ]

    for name, sql in test_cases:
        is_valid, message = validate_sql(sql)

        print(f"\n{name}")
        print(f"Result: {'PASS' if is_valid else 'REJECTED'}")
        print(f"Message: {message}")
