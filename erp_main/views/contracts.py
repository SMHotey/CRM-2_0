from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import Organization, InternalLegalEntity, Contract
from ..services.document_generator import ContractGenerator


@require_POST
def create_contract(request, pk):
    """Создание договора"""
    internal_legal_entity_id = request.POST.get('internal_legal_entity')
    internal_legal_entity = get_object_or_404(InternalLegalEntity, pk=internal_legal_entity_id)
    organization = get_object_or_404(Organization, pk=pk)

    generator = ContractGenerator()

    try:
        file_path, contract_number = generator.generate_contract(internal_legal_entity, organization)

        # Сохраняем информацию о договоре в базе
        new_contract = Contract(
            number=contract_number.replace("/", ""),
            organization=organization,
            internal_legal_entity=internal_legal_entity,
            days=21,  # стандартный срок
            file=file_path
        )
        new_contract.save()

        internal_legal_entities = InternalLegalEntity.objects.all()
        new_contract_url = file_path.replace('media/', '/media/')  # Формируем URL

        return render(request, 'organization_detail.html', {
            'organization': organization,
            'new_contract_url': new_contract_url,
            'internal_legal_entities': internal_legal_entities,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при создании договора: {str(e)}'
        }, status=500)