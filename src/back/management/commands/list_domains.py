from django.core.management.base import BaseCommand

from back.models.domain import Domain


class Command(BaseCommand):

    help = 'Print all known domain names'

    def handle(self, *args, **options):
        for domain_obj in Domain.domains.all():
            print(domain_obj.name)
