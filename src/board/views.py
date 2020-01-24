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
