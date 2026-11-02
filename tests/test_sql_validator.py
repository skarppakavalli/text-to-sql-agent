import pytest
from app.sql_validator import validate_sql

@pytest.mark.parametrize(
    "sql, expected",
    [
        # Valid SELECT queries
        ("SELECT * FROM customer", True),

        (
            "SELECT name, city FROM customer "
            "WHERE country = 'India'",
            True,
        ),

        (
            """SELECT c.first_name, i.total
               FROM customer c
               JOIN invoice i
               ON c.customer_id = i.customer_id""",
            True,
        ),

        ("SELECT * FROM customer LIMIT 5 OFFSET 2", True),

        (
            """SELECT country, COUNT(*)
               FROM customer
               GROUP BY country
               HAVING COUNT(*) > 5""",
            True,
        ),

        (
            """SELECT * FROM customer
               WHERE customer_id IN (
                   SELECT customer_id FROM invoice
               )""",
            True,
        ),

        (
            """SELECT artist_id FROM album
               UNION
               SELECT artist_id FROM album WHERE artist_id = 1""",
            True,
        ),

        (
            """WITH sales AS (
                   SELECT customer_id, SUM(total) AS amount
                   FROM invoice
                   GROUP BY customer_id
               )
               SELECT * FROM sales""",
            True,
        ),

        # Invalid operations
        ("DELETE FROM customer WHERE customer_id = 1", False),
        ("UPDATE customer SET city = 'Chennai'", False),
        ("DROP TABLE customer", False),
        ("SELECT * INTO customer_backup FROM customer", False),

        # Invalid table/schema references
        ("SELECT * FROM employees", False),
        ("SELECT * FROM private.customer", False),
        ("SELECT * FROM otherdb.public.customer", False),

        # Invalid SQL structure
        (
            "SELECT * FROM customer; SELECT * FROM invoice",
            False,
        ),
        ("SELEC * FROM customer", False),

        # Nested DML
        (
            """WITH x AS (
                   DELETE FROM customer RETURNING *
               )
               SELECT * FROM x""",
            False,
        ),

        # Locking
        ("SELECT * FROM customer FOR UPDATE", False),

        # CTE and scope validation
        (
            """WITH sales AS (
                   SELECT * FROM invoice
               )
               SELECT * FROM sales""",
            True,
        ),

        (
            """WITH sales AS (
                   SELECT * FROM unknown_table
               )
               SELECT * FROM sales""",
            False,
        ),

        (
            """SELECT * FROM customer_sales
               WHERE customer_id IN (
                   WITH customer_sales AS (
                       SELECT customer_id FROM invoice
                   )
                   SELECT customer_id FROM customer_sales
               )""",
            False,
        ),
    ],
)
def test_validate_sql(sql, expected):
    is_valid, message = validate_sql(sql)

    assert is_valid == expected, (
        f"\nSQL: {sql}\n"
        f"Expected: {expected}\n"
        f"Actual: {is_valid}\n"
        f"Message: {message}"
    )
