import pymysql


def clear_all_tables(host, user, password, db):
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db
        )

        cursor = conn.cursor()

        # Получаем список всех таблиц
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]

            # Очищаем таблицу (DELETE FROM удаляет данные, сохраняя структуру)
            print(f"Очистка таблицы {table_name}")
            cursor.execute(f"DELETE FROM `{table_name}`")

        conn.commit()  # Применяем изменения
        print("Все таблицы очищены.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        if conn.open:
            conn.close()


if __name__ == "__main__":
    # Измените значения на ваши собственные учетные данные
    HOST = "localhost"
    USER = "smhotey"
    PASSWORD = "64Fiz9ka"
    DB_NAME = "CRM"


    clear_all_tables(HOST, USER, PASSWORD, DB_NAME)