import json

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import Certificate, InternalLegalEntity, Nameplate
from ..forms import CertificateForm


class CertificateListView(LoginRequiredMixin, ListView):
    model = Certificate
    template_name = 'certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 20

    def get_queryset(self):
        queryset = Certificate.objects.select_related('internal_legal_entity').order_by('-id')

        # Фильтрация по поисковому запросу
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(numbers__icontains=search_query) |
                Q(p_kind__icontains=search_query) |
                Q(p_type__icontains=search_query) |
                Q(internal_legal_entity__name__icontains=search_query)
            )

        # Фильтрация по юридическому лицу
        internal_legal_entity_id = self.request.GET.get('internal_legal_entity')
        if internal_legal_entity_id:
            queryset = queryset.filter(internal_legal_entity_id=internal_legal_entity_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['internal_legal_entities'] = InternalLegalEntity.objects.all()
        context['selected_internal_legal_entity'] = self.request.GET.get('internal_legal_entity')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class CertificateDetailView(LoginRequiredMixin, DetailView):
    model = Certificate
    template_name = 'certificate_detail.html'
    context_object_name = 'certificate'


class CertificateCreateView(LoginRequiredMixin, CreateView):
    model = Certificate
    form_class = CertificateForm
    template_name = 'certificate_form.html'
    success_url = reverse_lazy('certificate_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['internal_legal_entities'] = InternalLegalEntity.objects.all()
        return context

    def form_valid(self, form):
        # Можно добавить дополнительную логику при создании
        return super().form_valid(form)


class CertificateUpdateView(LoginRequiredMixin, UpdateView):
    model = Certificate
    form_class = CertificateForm
    template_name = 'certificate_form.html'
    success_url = reverse_lazy('certificate_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['internal_legal_entities'] = InternalLegalEntity.objects.all()
        context['certificate'] = self.get_object()
        return context


class CertificateDeleteView(LoginRequiredMixin, DeleteView):
    model = Certificate
    template_name = 'certificate_confirm_delete.html'
    success_url = reverse_lazy('certificate_list')


@require_http_methods(["GET"])
def get_certificates(request):
    kind = request.GET.get('kind')
    type = request.GET.get('type')

    certificates = Certificate.objects.filter(
        p_kind=kind,
        p_type=type
    ).select_related('internal_legal_entity')

    certificates_data = []
    for cert in certificates:
        certificates_data.append({
            'id': cert.id,
            'numbers': cert.numbers,
            'internal_legal_entity_name': cert.internal_legal_entity.name
        })

    return JsonResponse(certificates_data, safe=False)


@require_http_methods(["GET"])
def get_nameplates(request):
    order_item_id = request.GET.get('order_item_id')

    nameplates = Nameplate.objects.filter(
        order_item_id=order_item_id
    ).select_related('certificate')

    nameplates_data = []
    for np in nameplates:
        nameplates_data.append({
            'certificate_numbers': np.certificate.numbers,
            'first_value': np.first_value,
            'end_value': np.end_value,
            'issue_date': np.issue_date.strftime('%d.%m.%Y') if np.issue_date else None
        })

    return JsonResponse(nameplates_data, safe=False)


@require_http_methods(["POST"])
@csrf_exempt
def create_nameplate(request):
    try:
        data = json.loads(request.body)

        nameplate = Nameplate.objects.create(
            order_item_id=data['order_item_id'],
            certificate_id=data['certificate_id'],
            first_value=data['first_value'],
            end_value=data.get('end_value'),
            issue_date=data['issue_date']
        )

        return JsonResponse({
            'success': True,
            'nameplate_id': nameplate.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# erp_main/views.py
@require_http_methods(["GET"])
def get_nameplate_data(request):
    nameplate_id = request.GET.get('nameplate_id')

    try:
        nameplate = Nameplate.objects.get(id=nameplate_id)
        nameplate_data = {
            'certificate_id': nameplate.certificate_id,
            'first_value': nameplate.first_value,
            'end_value': nameplate.end_value,
            'issue_date': nameplate.issue_date.strftime('%Y-%m-%d') if nameplate.issue_date else None
        }
        return JsonResponse(nameplate_data)
    except Nameplate.DoesNotExist:
        return JsonResponse({'error': 'Шильд не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def update_nameplate(request):
    try:
        data = json.loads(request.body)

        nameplate = Nameplate.objects.get(id=data['nameplate_id'])
        nameplate.certificate_id = data['certificate_id']
        nameplate.issue_date = data['issue_date']
        nameplate.first_value = data['first_value']
        nameplate.end_value = data.get('end_value')
        nameplate.save()

        return JsonResponse({
            'success': True,
            'nameplate_id': nameplate.id
        })

    except Nameplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Шильд не найден'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def delete_nameplate(request):
    try:
        data = json.loads(request.body)

        nameplate = Nameplate.objects.get(id=data['nameplate_id'])
        nameplate.delete()

        return JsonResponse({
            'success': True,
            'message': 'Шильд удален'
        })

    except Nameplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Шильд не найден'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)