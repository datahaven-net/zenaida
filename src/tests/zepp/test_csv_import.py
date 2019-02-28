import os
import pytest

from zepp import csv_import

from zen import zdomains
from zen import zusers 


@pytest.mark.django_db
def test_domain_regenerate_from_csv_row_dry_run():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), 'domains_sample.csv'))
    assert csv_import.load_from_csv(filename, dry_run=True) == 2
    assert zdomains.find('test-import-1.ai') is None
    assert zdomains.find('test-import-2.ai') is None
    assert zusers.find_account('test1@gmail.com') is None
    assert zusers.find_account('test2@gmail.com') is None


@pytest.mark.django_db
def test_domain_regenerate_from_csv_row():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), 'domains_sample.csv'))
    assert csv_import.load_from_csv(filename, dry_run=False) == 2
    domain1 = zdomains.find('test-import-1.ai')
    user1 = zusers.find_account('test1@gmail.com')
    assert domain1 is not None
    assert user1 is not None
    assert domain1.registrant.epp_id == 'epp2025164ehqs'
    assert domain1.contact_admin.epp_id == 'epp2024611d4ru'
    assert domain1.list_nameservers() == ['facebook.com', 'google.com', '', '', ]
    domain2 = zdomains.find('test-import-2.ai')
    user2 = zusers.find_account('test2@gmail.com')
    assert user2 is not None
    assert domain2 is not None
    assert domain2.registrant.epp_id == 'epp583472wixr'
    assert domain2.contact_admin.epp_id == 'epp583456ht51'
    assert domain2.list_nameservers() == ['ns1.google.com', 'ns2.google.com', 'ns3.google.com', '']
