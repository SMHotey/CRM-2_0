document.addEventListener('DOMContentLoaded', function() {
    const typeField = document.querySelector('#id_type');

    function toggleFields() {
        const selectedType = typeField.value;

        // Все возможные группы полей
        const allFieldGroups = [
            'field-name', 'field-inn', 'field-ogrn', 'field-kpp',
            'field-legal_address', 'field-postal_address',
            'field-ceo_title', 'field-ceo_name', 'field-email',
            'field-bank_name', 'field-account_number', 'field-bik', 'field-correspondent_account'
        ];

        // Сначала скрываем все поля кроме type
        allFieldGroups.forEach(fieldId => {
            const fieldElement = document.querySelector(`.${fieldId}`);
            if (fieldElement) {
                fieldElement.style.display = 'none';
            }
        });

        // Показываем поля в зависимости от типа
        if (selectedType === 'WITHOUT_INVOICE') {
            // Показываем только поле type (оно всегда видно)
            return;
        }
        else if (selectedType === 'INDIVIDUAL') {
            // Поля для ИП
            showFields(['field-ceo_name', 'field-inn', 'field-ogrn', 'field-legal_address', 'field-email',
                       'field-bank_name', 'field-account_number', 'field-bik', 'field-correspondent_account']);
        }
        else if (selectedType === 'LEGAL') {
            // Поля для ООО
            showFields(['field-name', 'field-inn', 'field-ogrn', 'field-kpp', 'field-legal_address',
                       'field-postal_address', 'field-ceo_title', 'field-ceo_name', 'field-email',
                       'field-bank_name', 'field-account_number', 'field-bik', 'field-correspondent_account']);
        }
    }

    function showFields(fieldIds) {
        fieldIds.forEach(fieldId => {
            const fieldElement = document.querySelector(`.${fieldId}`);
            if (fieldElement) {
                fieldElement.style.display = 'block';
            }
        });
    }

    // Вызываем при загрузке страницы
    toggleFields();

    // И при изменении типа
    if (typeField) {
        typeField.addEventListener('change', toggleFields);
    }

    // Также обрабатываем динамическое добавление форм в стэке
    document.addEventListener('formset:added', function(event) {
        if (event.target.querySelector('#id_type')) {
            toggleFields();
        }
    });
});