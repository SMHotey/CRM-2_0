# fix_migrations.py
import os
import subprocess
import sys


def fix_migration_dependencies():
    print("Исправление зависимостей миграций...")

    # Удаляем все миграции кроме __init__.py
    apps = ['erp_main', 'calculation']

    for app in apps:
        mig_dir = os.path.join(app, 'migrations')
        if os.path.exists(mig_dir):
            for file in os.listdir(mig_dir):
                if file.endswith('.py') and file != '__init__.py':
                    file_path = os.path.join(mig_dir, file)
                    os.remove(file_path)
                    print(f"Удален: {file_path}")

    # Создаем миграции по очереди
    print("\nСоздание миграций для erp_main...")
    subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'erp_main'], check=True)

    print("\nСоздание миграций для calculation...")
    subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'calculation'], check=True)

    print("\nПрименение миграций...")
    subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)

    print("✓ Миграции исправлены!")


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Journal_4_0.settings')
    fix_migration_dependencies()