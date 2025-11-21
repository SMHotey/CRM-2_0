# reset_database.py
import os
import sys
import subprocess
import MySQLdb
from django.conf import settings


def execute_sql(command):
    """Выполняет SQL команду"""
    try:
        conn = MySQLdb.connect(
            host=settings.DATABASES['default']['HOST'],
            user=settings.DATABASES['default']['USER'],
            passwd=settings.DATABASES['default']['PASSWORD'],
            port=int(settings.DATABASES['default'].get('PORT', 3306))
        )
        cursor = conn.cursor()
        cursor.execute(command)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка SQL: {e}")
        return False


def delete_migration_files():
    """Удаляет все файлы миграций кроме __init__.py"""
    print("Удаление старых миграций...")

    migration_files_deleted = []

    for root, dirs, files in os.walk('.'):
        if 'migrations' in dirs:
            mig_dir = os.path.join(root, 'migrations')
            for file in os.listdir(mig_dir):
                file_path = os.path.join(mig_dir, file)
                if file != '__init__.py' and (file.endswith('.py') or file.endswith('.pyc')):
                    try:
                        os.remove(file_path)
                        migration_files_deleted.append(file_path)
                        print(f"Удален: {file_path}")
                    except Exception as e:
                        print(f"Не удалось удалить {file_path}: {e}")

    return migration_files_deleted


def reset_database():
    print("=== ПЕРЕСОЗДАНИЕ БАЗЫ ДАННЫХ ===")

    # Получаем настройки БД
    db_config = settings.DATABASES['default']
    db_name = db_config['NAME']

    print(f"Настройки базы данных:")
    print(f"  Имя БД: {db_name}")
    print(f"  Пользователь: {db_config['USER']}")
    print(f"  Хост: {db_config['HOST']}")
    print(f"  Порт: {db_config.get('PORT', 3306)}")

    # Подтверждение действия
    response = input(f"\nВы уверены, что хотите удалить базу данных '{db_name}'? (yes/no): ")
    if response.lower() != 'yes':
        print("Отменено.")
        return

    print("\n1. Удаление и создание базы данных...")

    # Удаляем базу данных
    if execute_sql(f"DROP DATABASE IF EXISTS `{db_name}`"):
        print(f"✓ База данных '{db_name}' удалена")
    else:
        print("✗ Ошибка при удалении базы данных")
        return

    # Создаем базу данных заново
    if execute_sql(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"):
        print(f"✓ База данных '{db_name}' создана")
    else:
        print("✗ Ошибка при создании базы данных")
        return

    print("\n2. Очистка миграций...")
    deleted_files = delete_migration_files()
    print(f"✓ Удалено файлов миграций: {len(deleted_files)}")

    print("\n3. Создание новых миграций...")
    try:
        result = subprocess.run([sys.executable, 'manage.py', 'makemigrations'],
                                capture_output=True, text=True, check=True)
        print("✓ Новые миграции созданы")
        if result.stdout:
            print(f"   Вывод: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Ошибка при создании миграций: {e}")
        if e.stderr:
            print(f"   Ошибка: {e.stderr.strip()}")
        return

    print("\n4. Применение миграций...")
    try:
        result = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                                capture_output=True, text=True, check=True)
        print("✓ Миграции применены")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip() and 'Applying' in line:
                    print(f"   {line.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Ошибка при применении миграций: {e}")
        if e.stderr:
            print(f"   Ошибка: {e.stderr.strip()}")
        return

    print("\n5. Создание суперпользователя...")
    create_superuser = input("Создать суперпользователя? (yes/no): ")
    if create_superuser.lower() == 'yes':
        try:
            subprocess.run([sys.executable, 'manage.py', 'createsuperuser'], check=True)
            print("✓ Суперпользователь создан")
        except subprocess.CalledProcessError as e:
            print("✗ Ошибка при создании суперпользователя")

    print("\n=== ПЕРЕСОЗДАНИЕ ЗАВЕРШЕНО ===")
    print("\nПроверьте работу сайта:")
    print("python manage.py runserver")


def check_dependencies():
    """Проверяет необходимые зависимости"""
    try:
        import MySQLdb
        return True
    except ImportError:
        print("Ошибка: Не установлен mysqlclient.")
        print("Установите: pip install mysqlclient")
        return False


if __name__ == '__main__':
    # Настройка окружения Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Journal_4_0.settings')

    try:
        import django

        django.setup()
    except Exception as e:
        print(f"Ошибка при настройке Django: {e}")
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    reset_database()