import sqlglot
from sqlglot.optimizer.scope import traverse_scope

sql = """
WITH customer AS (
    SELECT * FROM invoice
)
SELECT *
FROM customer;
"""

tree = sqlglot.parse_one(sql, read="postgres")

for scope in traverse_scope(tree):
    print("\n--- Scope ---")
    print("Expression:", scope.expression)
    print("Sources:", scope.sources)
    print("Tables:", scope.tables)
