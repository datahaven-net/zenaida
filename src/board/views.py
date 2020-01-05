from django import shortcuts
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from accounts.users import list_all_users_by_date
from base.mixins import StaffRequiredMixin
from billing import forms as billing_forms
from billing.orders import list_all_processed_orders_by_date


class FinancialReportView(StaffRequiredMixin, FormView):
    template_name = 'board/financial_report.html'
    form_class = billing_forms.FilterOrdersByDateForm
    success_url = reverse_lazy('financial_report')

    def post(self, request, *args, **kwargs):
        form = billing_forms.FilterOrdersByDateForm(request.POST)
        if form.data.get('year') or (form.data.get('year') and form.data.get('month')):
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

            return shortcuts.render(
                request=request,
                template_name='board/financial_report.html',
                context={
                    'form': self.form_class,
                    'object_list': order_items,
                    'total_payment_by_users': total_payment,
                    'total_registered_users': len(list_all_users_by_date(form.data.get('year'), form.data.get('month')))
                }
            )
        return super().post(request, *args, **kwargs)
