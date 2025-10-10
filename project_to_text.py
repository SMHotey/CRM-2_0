import os
import argparse


def is_project_file(file_path, extensions, exclude_dirs):
    # Проверяем расширение файла
    if not any(file_path.endswith(ext) for ext in extensions):
        return False

    # Исключаем системные директории
    exclude_patterns = exclude_dirs + [
        '__pycache__',
        '.git',
        '.idea',
        'venv',
        '.venv',
        'env',
        'node_modules',
        '.pytest_cache',
        'dist',
        'build'
    ]

    for pattern in exclude_patterns:
        if pattern in file_path.split(os.sep):
            return False

    return True


def collect_project_files(root_dir, extensions, exclude_dirs):
    project_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_dir)

            if is_project_file(rel_path, extensions, exclude_dirs):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    project_files.append((filename, rel_path, content))
                except (UnicodeDecodeError, PermissionError):
                    # Пропускаем бинарные файлы и файлы без доступа
                    continue
    return project_files


def main():
    parser = argparse.ArgumentParser(description='Сборщик файлов проекта PyCharm')
    parser.add_argument('--root', default='.', help='Корневая директория проекта')
    parser.add_argument('--output', default='project_content.txt', help='Выходной файл')
    parser.add_argument('--extensions', nargs='+', default=['.py', '.html', '.css', '.js', '.json', '.txt', '.md'],
                        help='Расширения файлов для включения')
    parser.add_argument('--exclude-dirs', nargs='+', default=['venv', 'env', 'external'],
                        help='Директории для исключения')

    args = parser.parse_args()

    print(f"Поиск файлов в {os.path.abspath(args.root)}...")
    project_files = collect_project_files(args.root, args.extensions, args.exclude_dirs)

    with open(args.output, 'w', encoding='utf-8') as f:
        for filename, rel_path, content in project_files:
            f.write(f"{'=' * 60}\n")
            f.write(f"Файл: {filename}\n")
            f.write(f"Путь: {rel_path}\n")
            f.write(f"Содержимое:\n{content}\n\n")

    print(f"Найдено файлов: {len(project_files)}")
    print(f"Результат сохранен в: {args.output}")


if __name__ == "__main__":
    main()