import datetime

from django.utils.timezone import make_aware
from django.conf import settings

from back import contacts
from back import domains
from back import users


def prepare_tester_account(email='tester@zenaida.ai', account_password='tester'):
    tester = users.find_account(email)
    if not tester:
        tester = users.create_account(email, account_password=account_password, is_active=True, )
    return tester


def prepare_tester_contact(tester=None):
    if not tester:
        tester = prepare_tester_account()
    tester_contact = tester.contacts.first()
    if not tester_contact:
        tester_contact = contacts.create(
            epp_id=None,
            owner=tester,
            person_name='Tester Tester',
            organization_name='TestingCorp',
            address_street='TestStreet',
            address_city='TestCity',
            address_province='TestProvince',
            address_postal_code='TestPostalCode',
            address_country='TestCountry',
            contact_voice='1234567890',
            contact_fax='1234567890',
            contact_email='tester@zenaida.ai',
        )
    return tester_contact


def prepare_tester_domain(
        domain_name,
        tester=None,
        auth_key='',
        domain_epp_id=None,
        add_contacts=['registrant', 'admin', 'billing', 'tech', ],
        epp_id_dict={},
        nameservers=['ns1.google.com', 'ns2.google.com', ],
    ):
    if not tester:
        tester = prepare_tester_account()
    tester_registrant = contacts.create(
        epp_id=epp_id_dict.get('registrant'),
        owner=tester,
        person_name='Tester Tester Registrant',
        organization_name='TestingCorp',
        address_street='TestStreet',
        address_city='TestCity',
        address_province='TestProvince',
        address_postal_code='TestPostalCode',
        address_country='TestCountry',
        contact_voice='1234567890',
        contact_fax='1234567890',
        contact_email='tester@zenaida.ai',
    ) if 'registrant' in add_contacts else None
    tester_contact_admin = contacts.create(
        epp_id=epp_id_dict.get('admin'),
        owner=tester,
        person_name='Tester Tester Admin',
        organization_name='TestingCorp',
        address_street='TestStreet',
        address_city='TestCity',
        address_province='TestProvince',
        address_postal_code='TestPostalCode',
        address_country='TestCountry',
        contact_voice='1234567890',
        contact_fax='1234567890',
        contact_email='tester@zenaida.ai',
    ) if 'admin' in add_contacts else None
    tester_contact_tech = contacts.create(
        epp_id=epp_id_dict.get('tech'),
        owner=tester,
        person_name='Tester Tester Tech',
        organization_name='TestingCorp',
        address_street='TestStreet',
        address_city='TestCity',
        address_province='TestProvince',
        address_postal_code='TestPostalCode',
        address_country='TestCountry',
        contact_voice='1234567890',
        contact_fax='1234567890',
        contact_email='tester@zenaida.ai',
    ) if 'tech' in add_contacts else None
    tester_contact_billing = contacts.create(
        epp_id=epp_id_dict.get('billing'),
        owner=tester,
        person_name='Tester Tester Billing',
        organization_name='TestingCorp',
        address_street='TestStreet',
        address_city='TestCity',
        address_province='TestProvince',
        address_postal_code='TestPostalCode',
        address_country='TestCountry',
        contact_voice='1234567890',
        contact_fax='1234567890',
        contact_email='tester@zenaida.ai',
    ) if 'billing' in add_contacts else None
    tester_domain = domains.create(
        domain_name=domain_name,
        owner=tester,
        expiry_date=make_aware(datetime.datetime.now() + datetime.timedelta(days=365)),
        create_date=make_aware(datetime.datetime.now()),
        epp_id=domain_epp_id,
        auth_key=auth_key,
        registrar=None,
        registrant=tester_registrant,
        contact_admin=tester_contact_admin,
        contact_tech=tester_contact_tech,
        contact_billing=tester_contact_billing,
        nameservers=nameservers,
    )
    return tester_domain
