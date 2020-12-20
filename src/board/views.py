import os
import logging
import tempfile

from io import StringIO

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from accounts.users import list_all_users_by_date
from base.mixins import StaffRequiredMixin
from billing import forms as billing_forms
from billing.orders import list_all_processed_orders_by_date
from board.forms import DomainSyncForm, CSVFileSyncForm
from back.csv_import import load_from_csv
from zen import zmaster, zdomains

logger = logging.getLogger(__name__)


class FinancialReportView(StaffRequiredMixin, FormView):
    template_name = 'board/financial_report.html'
    form_class = billing_forms.FilterOrdersByDateForm
    success_url = reverse_lazy('financial_report')

    def form_valid(self, form):
        year = form.cleaned_data.get('year')
        month = form.cleaned_data.get('month')
        if year or (year and month):
            orders_for_specific_time = list_all_processed_orders_by_date(
                year=form.data.get('year'),
                month=form.data.get('month')
            )

            order_items = []
            total_payment = 0

            for order in orders_for_specific_time:
                for order_item in order.items.all():
                    order_items.append(order_item)
                    total_payment += order_item.price
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    object_list=order_items,
                    total_payment_by_users=total_payment,
                    total_registered_users=len(list_all_users_by_date(year, month))
                )
            )
        return super().form_valid(form)


class NotExistingDomainSyncView(StaffRequiredMixin, FormView):
    template_name = 'board/not_existing_domain_sync.html'
    form_class = DomainSyncForm
    success_url = reverse_lazy('not_existing_domain_sync')

    def form_valid(self, form):
        domain_name = form.cleaned_data.get('domain_name')
        zmaster.domain_synchronize_from_backend(
            domain_name=form.cleaned_data.get('domain_name'),
            refresh_contacts=True,
            rewrite_contacts=False,
            change_owner_allowed=True,
            create_new_owner_allowed=True,
            soft_delete=True,
            raise_errors=True,
            log_events=True,
            log_transitions=True,
        )

        domain_in_db = zdomains.domain_find(domain_name=domain_name)
        if domain_in_db:
            logger.info(f'{domain_name} is successfully synced.')
            messages.success(self.request, f'{domain_name} is successfully synced.')
        else:
            messages.warning(self.request, f'Something went wrong during sync of {domain_name}')

        return super().form_valid(form)


class CSVFileSyncView(StaffRequiredMixin, FormView):
    template_name = 'board/csv_file_sync.html'
    form_class = CSVFileSyncForm
    success_url = reverse_lazy('csv_file_sync')
    output_result = ''

    def form_valid(self, form):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                output_result=self.output_result,
            )
        )

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('csv_file')
        if not form.is_valid():
            return self.form_invalid(form)

        log_stream = StringIO()
        string_handler = logging.StreamHandler(log_stream)
        string_logger = logging.getLogger('')
        string_logger.setLevel(logging.DEBUG)
        string_logger.addHandler(string_handler)

        total_count = 0

        for f in files:
            fout, csv_file_path = tempfile.mkstemp(suffix='.csv', prefix='domains', dir='/tmp')
            string_logger.info('processing {}\n'.format(csv_file_path))

            while True:
                chunk = f.file.read(100000)
                if not chunk:
                    break
                os.write(fout, chunk)
            os.close(fout)

            try:
                ret = load_from_csv(
                    filename=csv_file_path,
                    dry_run=bool(form.data.get('dry_run', True)),
                    log=string_logger,
                )
            except:
                string_logger.exception()
                ret = -1

            os.remove(csv_file_path)

            if ret < 0:
                continue
            total_count += ret

        string_logger.info('total records processed: %d', total_count)

        self.output_result = log_stream.getvalue()
        return self.form_valid(form)
