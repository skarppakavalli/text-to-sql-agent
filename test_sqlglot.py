import sqlglot

sql = """
SELECT name, city
FROM customer
WHERE country = 'India'
"""

tree = sqlglot.parse_one(sql, read="postgres")

print(tree)
print(type(tree))

for node in tree.walk():
    print(type(node).__name__, "->", node)