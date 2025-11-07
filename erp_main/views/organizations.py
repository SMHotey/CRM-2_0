from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, ListView, DetailView

from ..models import Organization, LegalEntity
from ..forms import OrganizationForm, LegalEntityForm
from .mixins import UserAccessMixin

class OrganizationCreateView(UserAccessMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_add.html'

    def form_valid(self, form):
        organization = form.save(commit=False)
        organization.user = self.request.user
        organization.save()
        return redirect('organization_list')

class OrganizationUpdateView(UserAccessMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_edit.html'
    context_object_name = 'organization'

    def get_success_url(self):
        return reverse('organization_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        organization = form.save(commit=False)
        type_ = form.cleaned_data.get('type')

        if type_ == 'organization':
            organization.name_fl = None
            organization.phone_number = None
        elif type_ == 'individual':
            organization.name = None
            organization.inn = None
            organization.ogrn = None
            organization.kpp = None
            organization.r_s = None
            organization.bank = None
            organization.bik = None
            organization.k_s = None
            organization.ceo_title = None

        organization.save()
        return super().form_valid(form)

class OrganizationListView(UserAccessMixin, ListView):
    model = Organization
    template_name = 'organization_list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        return self.get_user_organizations()

class OrganizationDetailView(UserAccessMixin, DetailView):
    model = Organization
    template_name = 'organization_detail.html'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['legal_entities'] = LegalEntity.objects.all()
        return context

def create_legal_entity(request):
    if request.method == 'POST':
        form = LegalEntityForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('organization_list')
    else:
        form = LegalEntityForm(request.user)

    return render(request, 'legal_entity_form.html', {'form': form})