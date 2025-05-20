import json

with open('new_dump.json', 'r', encoding='utf-8-sig') as f:  # Обрабатываем BOM
    data = json.load(f)

with open('fixed_dump.json', 'w', encoding='utf-8') as f:  # Сохраняем без BOM
    json.dump(data, f, indent=2, ensure_ascii=False)