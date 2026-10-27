import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(DATABASE_URL)


def get_database_schema() -> str:
    inspector = inspect(engine)
    schema_name = "public"
    schema_parts = []

    table_names = inspector.get_table_names(schema=schema_name)

    for table_name in sorted(table_names):
        columns = inspector.get_columns(
            table_name,
            schema=schema_name,
        )

        primary_key = inspector.get_pk_constraint(
            table_name,
            schema=schema_name,
        )

        primary_key_columns = set(
            primary_key.get("constrained_columns") or []
        )

        lines = [f"Table: {table_name}", "Columns:"]

        for column in columns:
            name = column["name"]
            data_type = str(column["type"])
            nullable = column["nullable"]

            details = [data_type]

            if name in primary_key_columns:
                details.append("PRIMARY KEY")

            if not nullable:
                details.append("NOT NULL")

            lines.append(
                f"  - {name}: {', '.join(details)}"
            )

        foreign_keys = inspector.get_foreign_keys(
            table_name,
            schema=schema_name,
        )

        if foreign_keys:
            lines.append("Foreign keys:")

            for fk in foreign_keys:
                source_columns = ", ".join(
                    fk["constrained_columns"]
                )
                target_columns = ", ".join(
                    fk["referred_columns"]
                )
                target_table = fk["referred_table"]

                lines.append(
                    f"  - ({source_columns}) references "
                    f"{target_table}({target_columns})"
                )

        schema_parts.append("\n".join(lines))

    return "\n\n".join(schema_parts)


if __name__ == "__main__":
    print(get_database_schema())