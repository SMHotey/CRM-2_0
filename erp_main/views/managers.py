# managers.py
from django.db import models
from django.contrib.contenttypes.models import ContentType


class OrganizationManager:
    @classmethod
    def get_all_counterparties(cls):
        """Получить всех контрагентов"""
        from ..models import LegalEntity, IndividualEntrepreneur, PhysicalPerson

        legal_entities = LegalEntity.objects.select_related('internal_legal_entity', 'user')
        individual_entrepreneurs = IndividualEntrepreneur.objects.select_related('internal_legal_entity', 'user')
        physical_persons = PhysicalPerson.objects.select_related('user')

        all_counterparties = list(legal_entities) + list(individual_entrepreneurs) + list(physical_persons)
        return sorted(all_counterparties, key=lambda x: x.created_at, reverse=True)

    @classmethod
    def find_by_inn(cls, inn):
        """Найти контрагента по ИНН (для юрлиц и ИП)"""
        from ..models import LegalEntity, IndividualEntrepreneur

        legal_entity = LegalEntity.objects.filter(inn=inn).select_related('internal_legal_entity').first()
        if legal_entity:
            return legal_entity

        individual_entrepreneur = IndividualEntrepreneur.objects.filter(inn=inn).select_related(
            'internal_legal_entity').first()
        if individual_entrepreneur:
            return individual_entrepreneur

        return None

    @classmethod
    def find_by_phone(cls, phone):
        """Найти контрагента по телефону (для физлиц)"""
        from ..models import PhysicalPerson
        return PhysicalPerson.objects.filter(phone=phone).first()

    @classmethod
    def get_by_internal_company(cls, internal_company):
        """Получить все контрагенты привязанные к определенному внутреннему юрлицу"""
        from ..models import LegalEntity, IndividualEntrepreneur

        legal_entities = LegalEntity.objects.filter(parent_company=internal_company)
        individual_entrepreneurs = IndividualEntrepreneur.objects.filter(parent_company=internal_company)

        return list(legal_entities) + list(individual_entrepreneurs)