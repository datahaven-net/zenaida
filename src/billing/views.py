import logging
import datetime

from dateutil.relativedelta import relativedelta
from django import shortcuts
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.core import exceptions
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView, FormView, DetailView, CreateView, ListView
from django.views.generic.edit import FormMixin

from billing import forms as billing_forms
from billing import orders as billing_orders
from billing import payments
from billing import billing_errors

from zen import zdomains


@login_required
def billing_overview(request):
    """
    """
    # TODO: this needs to be done
    pass


class PaymentsListView(LoginRequiredMixin, ListView):
    template_name = 'billing/account_payments.html'
    paginate_by = 10

    def get_queryset(self):
        return payments.list_payments(owner=self.request.user)


class NewPaymentView(LoginRequiredMixin, FormView):
    template_name = 'billing/new_payment.html'
    form_class = billing_forms.NewPaymentForm
    error_message = 'Payment method is invalid'
    success_url = reverse_lazy('billing_new_payment')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        if 'data' not in kw:
            kw['data'] = {
                'amount': self.request.GET.get('amount', '100'),
                'payment_method': self.form_class._get_payment_method_choices()[0][0]
            }
        return kw

    def form_valid(self, form):
        if settings.ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS:
            my_latest_unfinished_payment = payments.latest_payment(
                owner=self.request.user,
                status_in=['started', 'cancelled', 'declined', ],
            )
            if my_latest_unfinished_payment:
                if timezone.now() - my_latest_unfinished_payment.started_at < datetime.timedelta(
                    seconds=settings.ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS,
                ):
                    messages.info(self.request, 'Please wait few minutes and then try again.')
                    return shortcuts.redirect('billing_new_payment')

        new_payment = payments.start_payment(
            owner=self.request.user,
            amount=form.cleaned_data['amount'],
            payment_method=form.cleaned_data['payment_method'],
        )

        # TODO: for the future, if we need to implement other types of payments
        # https://www.dreamhost.com/blog/10-online-payment-gateways-compared/

        if new_payment.method == 'pay_4csonline':
            return shortcuts.render(
                self.request,
                'billing/4csonline/start_payment.html',
                {
                    'transaction_id': new_payment.transaction_id,
                }
            )

        elif new_payment.method == 'pay_btcpay':
            return shortcuts.render(
                self.request,
                'billing/btcpay/start_payment.html',
                {
                    'transaction_id': new_payment.transaction_id,
                    'amount': new_payment.amount
                }
            )

        messages.error(self.request, self.error_message)
        return super().form_valid(form)


class OrdersListView(LoginRequiredMixin, ListView, FormMixin):
    template_name = 'billing/account_orders.html'
    paginate_by = 10
    form_class = billing_forms.FilterOrdersByDateForm
    success_url = reverse_lazy('billing_orders')

    def get_queryset(self):
        if self.request.method == 'POST':
            form = self.form_class(self.request.POST)
            if form.is_valid():
                return billing_orders.list_orders_by_date(
                    owner=self.request.user,
                    year=form.data.get('year'),
                    month=form.data.get('month'),
                    exclude_cancelled=True,
                )
        return billing_orders.list_orders(owner=self.request.user, exclude_cancelled=True)

    def post(self, request, *args, **kwargs):
        return shortcuts.render(request, self.template_name, {'form': self.form_class, 'object_list': self.get_queryset()})


class OrderReceiptsDownloadView(LoginRequiredMixin, FormView):
    template_name = 'billing/account_invoices.html'
    form_class = billing_forms.FilterOrdersByDateForm
    success_url = reverse_lazy('billing_receipts_download')

    def form_valid(self, form):
        year = form.cleaned_data.get('year')
        month = form.cleaned_data.get('month')
        if year or (year and month):
            pdf_info = billing_orders.build_receipt(
                owner=self.request.user,
                year=form.data.get('year'),
                month=form.data.get('month'),
            )
            if not pdf_info:
                messages.warning(self.request, 'No orders found for given period')
                return self.render_to_response(
                    self.get_context_data(
                        form=form
                    )
                )
            response = HttpResponse(pdf_info['body'], content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
            return response
        return super().form_valid(form)


class OrderSingleReceiptDownloadView(View):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pdf_info = None
        if kwargs.get('order_id'):
            pdf_info = billing_orders.build_receipt(
                owner=request.user,
                order_id=kwargs.get('order_id'),
            )
        if not pdf_info:
            messages.warning(request, 'Order not found')
            return shortcuts.redirect('billing_orders')
        response = HttpResponse(pdf_info['body'], content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
        return response


class OrderDomainRegisterView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        new_order = billing_orders.order_single_item(
            owner=self.request.user,
            item_type='domain_register',
            item_price=settings.ZENAIDA_DOMAIN_PRICE,
            item_name=kwargs.get('domain_name'),
        )
        context.update({'order': new_order})
        context['domain_expiry_date'] = ''
        domain = zdomains.domain_find(domain_name=kwargs.get('domain_name'))
        if domain:
            context['domain_expiry_date'] = domain.expiry_date
        return context


class OrderDomainRenewView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        renewal_order = billing_orders.order_single_item(
            owner=self.request.user,
            item_type='domain_renew',
            item_price=settings.ZENAIDA_DOMAIN_PRICE,
            item_name=kwargs.get('domain_name'),
        )
        context.update({'order': renewal_order})
        context['domain_expiry_date'] = ''
        domain = zdomains.domain_find(domain_name=kwargs.get('domain_name'))
        if domain:
            context['domain_expiry_date'] = domain.expiry_date + relativedelta(years=2)
        return context


class OrderDomainRestoreView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        restore_order = billing_orders.order_single_item(
            owner=self.request.user,
            item_type='domain_restore',
            item_price=settings.ZENAIDA_DOMAIN_RESTORE_PRICE,
            item_name=kwargs.get('domain_name'),
        )
        context.update({'order': restore_order})
        context['domain_expiry_date'] = timezone.now() + relativedelta(years=2)
        return context


class OrderCreateView(LoginRequiredMixin, CreateView):
    error_message = 'No domains were selected'

    def post(self, request, *args, **kwargs):
        order_items = request.POST.getlist('order_items')
        to_be_ordered = []
        for domain_name in order_items:
            domain_object = zdomains.domain_find(domain_name=domain_name)
            if not domain_object:
                raise Http404
            if domain_object.owner != request.user:
                logging.critical('User %s tried to make an order with domain from another owner' % request.user)
                raise exceptions.SuspiciousOperation()
            try:
                item_type, item_price, item_name = billing_orders.prepare_register_renew_restore_item(domain_object)
            except billing_errors.DomainBlockedError as err:
                messages.error(request, str(err))
                return shortcuts.redirect('account_domains')
            to_be_ordered.append(dict(
                item_type=item_type,
                item_price=item_price,
                item_name=item_name,
            ))
        if not to_be_ordered:
            messages.error(request, self.error_message)
            return shortcuts.redirect('account_domains')
        new_order = billing_orders.order_multiple_items(
            owner=request.user,
            order_items=to_be_ordered,
        )
        return shortcuts.render(request, 'billing/order_details.html', {'order': new_order})


class OrderDetailsView(LoginRequiredMixin, DetailView):
    template_name = 'billing/order_details.html'

    def get_object(self, queryset=None):
        return billing_orders.get_order_by_id_and_owner(
            order_id=self.kwargs.get('order_id'), owner=self.request.user, log_action='check'
        )


class OrderExecuteView(LoginRequiredMixin, View):
    error_message_balance = 'Not enough funds on your balance to complete order. ' \
                            'Please buy more credits to be able to register/renew domains'
    error_message_technical = 'There is technical problem with order processing. ' \
                              'Please try again later or contact site administrator'
    success_message = 'Order processed successfully'
    processing_message = 'Order is processing, please wait'

    def post(self, request, *args, **kwargs):
        existing_order = billing_orders.get_order_by_id_and_owner(
            order_id=kwargs.get('order_id'), owner=request.user, log_action='execute'
        )
        if existing_order.total_price > existing_order.owner.balance:
            messages.error(request, self.error_message_balance)
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(existing_order.total_price - existing_order.owner.balance)))

        new_status = billing_orders.execute_order(existing_order)
        if new_status == 'processed':
            messages.success(request, self.success_message)
        elif new_status == 'processing':
            messages.success(request, self.processing_message)
        else:
            messages.error(request, self.error_message_technical)
        return shortcuts.redirect('account_domains')


class OrderCancelView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        existing_order = billing_orders.get_order_by_id_and_owner(
            order_id=kwargs.get('order_id'), owner=request.user, log_action='execute'
        )
        billing_orders.cancel_order(existing_order)
        messages.success(request, f'Order of {existing_order.description} is cancelled.')
        return shortcuts.redirect('billing_orders')
