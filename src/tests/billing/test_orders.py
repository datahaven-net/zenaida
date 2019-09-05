import pytest
import mock
from django.test import TestCase
from django.conf import settings

from billing import orders

from tests import testsupport


class TestOrders(TestCase):

    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @pytest.mark.django_db
    def test_order_domain_register_processed(self, mock_domain_check_create_update_renew):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_check_create_update_renew.return_value = True
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_register',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'processed'
        assert order_object.status == 'processed'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 900.0

    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @pytest.mark.django_db
    def test_order_domain_register_incomplete(self, mock_domain_check_create_update_renew):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_check_create_update_renew.return_value = False
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_register',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'failed'
        assert order_object.status == 'incomplete'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 1000.0

    @mock.patch('zen.zmaster.domain_transfer_request')
    @pytest.mark.django_db
    def test_order_domain_transfer_pending(self, mock_domain_transfer_request):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_transfer_request.return_value = True
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_transfer',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'transfer_code': 'abcd1234', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'pending'
        assert order_object.status == 'processing'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 1000.0

    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @pytest.mark.django_db
    def test_order_domain_renew_processed(self, mock_domain_check_create_update_renew):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_check_create_update_renew.return_value = True
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_renew',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'processed'
        assert order_object.status == 'processed'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 900.0

    @mock.patch('zen.zmaster.domain_restore')
    @pytest.mark.django_db
    def test_order_domain_restore_processed(self, mock_domain_restore):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_restore.return_value = True
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_restore',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'processed'
        assert order_object.status == 'processed'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 900.0

    @mock.patch('zen.zmaster.domain_transfer_request')
    @pytest.mark.django_db
    def test_refresh_order_domain_transfer_pending_to_processed(self, mock_domain_transfer_request):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.%s' % settings.ZENAIDA_SUPPORTED_ZONES[0],
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        tester_domain.owner.balance = 1000.0
        tester_domain.owner.save()
        mock_domain_transfer_request.return_value = True
        order_object = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_transfer',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'transfer_code': 'abcd1234', },
        )
        assert len(order_object.items.all()) == 1
        order_item = order_object.items.first()
        assert order_item.status == 'started'
        assert order_object.status == 'started'
        orders.execute_order(order_object)
        order_item.refresh_from_db()
        assert order_item.status == 'pending'
        assert order_object.status == 'processing'
        assert tester_domain.owner.balance == 1000.0
        orders.update_order_item(order_item, new_status='processed', charge_user=True)
        order_item.refresh_from_db()
        assert order_item.status == 'processed'
        orders.refresh_order(order_object)
        assert order_object.status == 'processed'
        tester_domain.owner.refresh_from_db()
        assert tester_domain.owner.balance == 900.0
