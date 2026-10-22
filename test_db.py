from db.database import get_connection


with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(), current_user"
        )

        result = cursor.fetchone()

        print(result)
        