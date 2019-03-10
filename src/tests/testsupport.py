import datetime

from django.utils.timezone import make_aware

from zen import zcontacts
from zen import zdomains
from zen import zusers


def prepare_tester_account(email='tester@zenaida.ai', account_password='tester'):
    tester = zusers.find_account(email)
    if not tester:
        tester = zusers.create_account(
            email,
            account_password=account_password,
            is_active=True,
            person_name='Tester Tester',
            organization_name='TestingCorp',
            address_street='TestStreet',
            address_city='TestCity',
            address_province='TestProvince',
            address_postal_code='TestPostalCode',
            address_country='AI',
            contact_voice='1234567890',
            contact_fax='1234567890',
            contact_email='tester@zenaida.ai',
        )
    return tester


def prepare_tester_contact(tester=None, epp_id=None, create_new=False):
    if not tester:
        tester = prepare_tester_account()
    tester_contact = tester.contacts.first()
    if not tester_contact or create_new:
        tester_contact = zcontacts.contact_create(
            epp_id=epp_id,
            owner=tester,
            person_name='Tester Tester',
            organization_name='TestingCorp',
            address_street='TestStreet',
            address_city='TestCity',
            address_province='TestProvince',
            address_postal_code='TestPostalCode',
            address_country='AI',
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
        nameservers=['notexist1.com', 'notexist2.com', ],
    ):
    if not tester:
        tester = prepare_tester_account()

    tester_registrant = zcontacts.registrant_create_from_profile(
        tester,
        profile_object=tester.profile,
        epp_id=epp_id_dict.get('registrant', '')
    ) if 'registrant' in add_contacts else None

    tester_contact_admin = prepare_tester_contact(
        tester,
        epp_id=epp_id_dict.get('admin', ''),
        create_new=True,
    ) if 'admin' in add_contacts else None

    tester_contact_tech = prepare_tester_contact(
        tester,
        epp_id=epp_id_dict.get('tech', ''),
        create_new=True,
    ) if 'tech' in add_contacts else None

    tester_contact_billing = prepare_tester_contact(
        tester,
        epp_id=epp_id_dict.get('billing', ''),
        create_new=True,
    ) if 'billing' in add_contacts else None

    tester_domain = zdomains.create(
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
