from django.db.models import Count
from django.core.management.base import BaseCommand

from back.models.contact import Contact, Registrant


class Command(BaseCommand):
    """
    Usage:

        ./venv/bin/python src/manage.py cleanup_unused_contacts

    """

    help = 'Removes all Contact and Registrant objects from the DB which are not attached to any domains'

    def handle(self, *args, **options):
        for cont in Contact.contacts.annotate(
            all_domains_count=Count("admin_domains", distinct=True) + Count("billing_domains", distinct=True) + Count("tech_domains", distinct=True)
        ).filter(all_domains_count=0):
            self.stdout.write('erasing %r\n' % cont)
            cont.delete()
        for reg in Registrant.registrants.annotate(all_domains_count=Count("registrant_domains", distinct=True)).filter(all_domains_count=0):
            self.stdout.write('erasing %r\n' % reg)
            reg.delete()
        self.stdout.write(self.style.SUCCESS('Done'))
