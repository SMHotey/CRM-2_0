from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import Organization, LegalEntity, Contract
from ..services.document_generator import ContractGenerator


@require_POST
def create_contract(request, pk):
    """Создание договора"""
    legal_entity_id = request.POST.get('legal_entity')
    legal_entity = get_object_or_404(LegalEntity, pk=legal_entity_id)
    organization = get_object_or_404(Organization, pk=pk)

    generator = ContractGenerator()

    try:
        file_path, contract_number = generator.generate_contract(legal_entity, organization)

        # Сохраняем информацию о договоре в базе
        new_contract = Contract(
            number=contract_number.replace("/", ""),
            organization=organization,
            legal_entity=legal_entity,
            days=21,  # стандартный срок
            file=file_path
        )
        new_contract.save()

        legal_entities = LegalEntity.objects.all()
        new_contract_url = file_path.replace('media/', '/media/')  # Формируем URL

        return render(request, 'organization_detail.html', {
            'organization': organization,
            'new_contract_url': new_contract_url,
            'legal_entities': legal_entities,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при создании договора: {str(e)}'
        }, status=500)