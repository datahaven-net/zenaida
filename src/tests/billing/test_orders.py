import datetime
import pytest
import mock
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from billing import orders

from tests import testsupport


class TestOrders(TestCase):

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
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
        mock_domain_check_create_update_renew.return_value = [True, ]
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

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
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
        mock_domain_check_create_update_renew.return_value = [False, ]
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

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_transfer_request')
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
        mock_domain_transfer_request.return_value = [True, ]
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

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_check_create_update_renew')
    @mock.patch('zen.zmaster.domain_synchronize_from_backend')
    def test_order_domain_renew_processed(self, mock_domain_check_create_update_renew, mock_domain_synchronize_from_backend):
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
        mock_domain_synchronize_from_backend.return_value = [True, ]
        mock_domain_check_create_update_renew.return_value = [True, ]
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

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_restore')
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
        mock_domain_restore.return_value = [True, ]
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

    @pytest.mark.django_db
    @mock.patch('zen.zmaster.domain_transfer_request')
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
        mock_domain_transfer_request.return_value = [True, ]
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

    def test_list_orders(self):
        tester_domain = testsupport.prepare_tester_domain(
            domain_name='testdomain.ai',
            add_contacts=['registrant', 'admin', ],
            epp_id_dict={
                'registrant': 'ThisIDNotExist1',
                'admin': 'ThisIDNotExist2',
            },
            nameservers=['notexist1.com', 'notexist2.com', ],
        )
        order_object_1 = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_register',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        order_object_1.finished_at = timezone.now() + datetime.timedelta(seconds=1)
        order_object_1.save()
        order_object_2 = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_renew',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        order_object_2.finished_at = timezone.now() + datetime.timedelta(seconds=2)
        order_object_2.save()
        order_object_3 = orders.order_single_item(
            owner=tester_domain.owner,
            item_type='domain_renew',
            item_price=100.0,
            item_name='testdomain.ai',
            item_details={'some': 'details', },
        )
        order_object_3.finished_at = timezone.now() + datetime.timedelta(seconds=3)
        order_object_3.save()
        l = orders.list_orders(tester_domain.owner, exclude_cancelled=True, include_statuses=['started', ])
        assert len(l) == 3
        assert l[0].id == order_object_3.id
        assert l[1].id == order_object_2.id
        assert l[2].id == order_object_1.id
