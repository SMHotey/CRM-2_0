document.addEventListener('DOMContentLoaded', function() {
    const typeField = document.querySelector('#id_type');

    function toggleFields() {
        const selectedType = typeField.value;

        // Все поля которые могут скрываться/показываться
        const allFields = [
            '.field-name', '.field-inn', '.field-ogrn', '.field-kpp',
            '.field-legal_address', '.field-postal_address',
            '.field-ceo_title', '.field-ceo_name', '.field-email',
            '.field-bank_name', '.field-account_number',
            '.field-bik', '.field-correspondent_account'
        ];

        // Скрываем все
        allFields.forEach(selector => {
            const el = document.querySelector(selector);
            if (el) el.style.display = 'none';
        });

        // Показываем нужные
        if (selectedType === 'INDIVIDUAL') {
            showFields([
                '.field-ceo_name', '.field-inn', '.field-ogrn',
                '.field-legal_address', '.field-email',
                '.field-bank_name', '.field-account_number',
                '.field-bik', '.field-correspondent_account'
            ]);
            updateLabelForAdmin('.field-ogrn', 'ОГРНИП');
        }
        else if (selectedType === 'LEGAL') {
            showFields([
                '.field-name', '.field-inn', '.field-ogrn', '.field-kpp',
                '.field-legal_address', '.field-postal_address',
                '.field-ceo_title', '.field-ceo_name', '.field-email',
                '.field-bank_name', '.field-account_number',
                '.field-bik', '.field-correspondent_account'
            ]);
            updateLabelForAdmin('.field-ogrn', 'ОГРН');
        }
    }

    function showFields(fieldSelectors) {
        fieldSelectors.forEach(selector => {
            const el = document.querySelector(selector);
            if (el) el.style.display = 'block';
        });
    }

    function updateLabelForAdmin(fieldSelector, newText) {
        const fieldDiv = document.querySelector(fieldSelector);
        if (!fieldDiv) return;

        // В админке есть несколько способов найти label:

        // Способ 1: Ищем label внутри fieldDiv
        const label = fieldDiv.querySelector('label');
        if (label) {
            // Сохраняем форматирование (двоеточие и т.д.)
            const currentText = label.textContent;
            if (currentText.includes(':')) {
                label.textContent = newText + ':';
            } else if (currentText.includes('*')) {
                // Если есть обязательное поле (*)
                label.textContent = newText + ' *';
            } else {
                label.textContent = newText;
            }
        }

        // Способ 2: Ищем input и обновляем placeholder
        const input = fieldDiv.querySelector('input, textarea, select');
        if (input) {
            input.placeholder = newText;
        }

        // Способ 3: Ищем текст "ОГРН" в любом элементе внутри fieldDiv
        const allElements = fieldDiv.querySelectorAll('*');
        for (let element of allElements) {
            if (element.textContent &&
                (element.textContent.includes('ОГРН') || element.textContent.includes('ОГРНИП'))) {
                // Заменяем ОГРН или ОГРНИП на новый текст
                element.textContent = element.textContent.replace(/ОГРН(ИП)?/, newText);
                break;
            }
        }
    }

    // Запускаем
    toggleFields();
    if (typeField) {
        typeField.addEventListener('change', toggleFields);
    }
});