import logging
import datetime

from dateutil.relativedelta import relativedelta  # @UnresolvedImport
from django import shortcuts
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView, FormView, DetailView, CreateView, ListView
from django.views.generic.edit import FormMixin

from billing import forms
from billing import orders
from billing import payments
from billing import exceptions
from billing.decorators import create_or_update_single_order

from zen import zdomains


class PaymentsListView(LoginRequiredMixin, ListView):
    template_name = 'billing/account_payments.html'
    paginate_by = 10

    def get_queryset(self):
        return payments.list_payments(owner=self.request.user)


class PaymentInvoiceDownloadView(View):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        transaction_id = kwargs.get('transaction_id')
        payment_obj = payments.by_transaction_id(transaction_id)
        if not payment_obj:
            messages.warning(request, "Invalid request, not possible to prepare invoice")
            return shortcuts.redirect('billing_payments')
        if payment_obj.owner != request.user:
            messages.warning(request, "Invalid request, not possible to prepare invoice")
            return shortcuts.redirect('billing_payments')
        pdf_info = payments.build_invoice(payment_obj)
        response = HttpResponse(pdf_info['body'], content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
        return response


class NewPaymentView(LoginRequiredMixin, FormView):
    template_name = 'billing/new_payment.html'
    form_class = forms.NewPaymentForm
    error_message = 'Payment method is invalid'
    success_url = reverse_lazy('billing_new_payment')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['credit_card_payment_price'] = round(settings.ZENAIDA_DOMAIN_PRICE * (
            (100.0 + settings.ZENAIDA_BILLING_4CSONLINE_BANK_COMMISSION_RATE) / 100.0), 2)
        context['credit_card_payment_base_price'] = settings.ZENAIDA_DOMAIN_PRICE
        return context

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        if 'data' not in kw:
            amount = self.request.GET.get('amount', str(int(settings.ZENAIDA_DOMAIN_PRICE)))
            amount = int(float(amount) / 10.0) * 10
            if not amount:
                amount = 10
            kw['data'] = {
                'amount': amount,
                'payment_method': self.form_class._get_payment_method_choices()[0][0]
            }
        return kw

    def form_valid(self, form):
        if settings.ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS:
            my_latest_unfinished_payment = payments.latest_payment(
                owner=self.request.user,
                status_in=['started', 'cancelled', 'declined', 'processed', 'paid', ],
            )
            if my_latest_unfinished_payment:
                if timezone.now() - my_latest_unfinished_payment.started_at < datetime.timedelta(
                    seconds=settings.ZENAIDA_BILLING_PAYMENT_TIME_FREEZE_SECONDS,
                ):
                    messages.info(self.request, 'Please wait few minutes and then try again.')
                    return shortcuts.redirect('billing_new_payment')

        my_pending_payment = payments.latest_payment(
            owner=self.request.user,
            status_in=['paid', ],
        )
        if my_pending_payment:
            messages.info(self.request, 'Your previous payment is pending for verification. Please wait few minutes before starting a new transaction.')
            return shortcuts.redirect('billing_payments')

        payment_method = form.cleaned_data['payment_method']
        payment_amount = float(form.cleaned_data['amount'])

        new_payment = payments.start_payment(
            owner=self.request.user,
            amount=payment_amount,
            payment_method=payment_method,
        )

        # TODO: for the future, if we need to implement other types of payments
        # https://www.dreamhost.com/blog/10-online-payment-gateways-compared/

        if payment_method == 'pay_4csonline':
            return shortcuts.render(
                self.request,
                'billing/4csonline/start_payment.html',
                {
                    'transaction_id': new_payment.transaction_id,
                }
            )

        elif payment_method == 'pay_btcpay':
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
    form_class = forms.FilterOrdersByDateForm
    success_url = reverse_lazy('billing_orders')

    def get_queryset(self):
        if self.request.method == 'POST':
            form = self.form_class(self.request.POST)
            if form.is_valid():
                return orders.list_orders_by_date(
                    owner=self.request.user,
                    year=form.data.get('year'),
                    month=form.data.get('month'),
                    exclude_cancelled=True,
                )
        return orders.list_orders(owner=self.request.user, exclude_cancelled=True)

    def post(self, request, *args, **kwargs):
        return shortcuts.render(request, self.template_name, {'form': self.form_class, 'object_list': self.get_queryset()})


class OrderReceiptsDownloadView(LoginRequiredMixin, FormView):
    template_name = 'billing/account_invoices.html'
    form_class = forms.FilterOrdersByDateForm
    success_url = reverse_lazy('billing_receipts_download')

    def form_valid(self, form):
        year = form.cleaned_data.get('year')
        month = form.cleaned_data.get('month')
        if year or (year and month):
            pdf_info = orders.build_receipt(
                owner=self.request.user,
                year=form.data.get('year'),
                month=form.data.get('month'),
            )
            if not pdf_info:
                messages.warning(self.request, 'Found no finished orders for given period')
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
        order_id = kwargs.get('order_id')
        if order_id:
            try:
                orders.get_order_by_id_and_owner(
                    order_id=order_id, owner=request.user, log_action="download a receipt for"
                )
            except SuspiciousOperation:
                messages.error(request, "Not possible to download this receipt file.")
                return shortcuts.redirect('billing_orders')

        pdf_info = orders.build_receipt(
            owner=request.user,
            order_id=order_id,
        )
        if not pdf_info:
            logging.critical('user %r tried to download a receipt file but no finished orders were found' % request.user)
            messages.error(request, "Not possible to download this receipt file.")
            return shortcuts.redirect('billing_orders')

        response = HttpResponse(pdf_info['body'], content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
        return response


class OrderDomainRegisterView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    @create_or_update_single_order(item_type='domain_register', item_price=settings.ZENAIDA_DOMAIN_PRICE)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'order': kwargs.get('order')})
        context['domain_expiry_date'] = ''
        domain = zdomains.domain_find(domain_name=kwargs.get('domain_name'))
        if domain:
            context['domain_expiry_date'] = domain.expiry_date
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if context.get('has_existing_order'):
            return shortcuts.redirect('billing_order_details', order_id=context.get('order').id)
        new_order = context.get('order')
        if new_order and new_order.total_price > new_order.owner.balance:
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(new_order.total_price - new_order.owner.balance)))
        return self.render_to_response(context)


class OrderDomainRenewView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    @create_or_update_single_order(item_type='domain_renew', item_price=settings.ZENAIDA_DOMAIN_PRICE)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'order': kwargs.get('order')})
        context['domain_expiry_date'] = ''
        domain = zdomains.domain_find(domain_name=kwargs.get('domain_name'))
        if domain:
            context['domain_expiry_date'] = domain.expiry_date + relativedelta(years=settings.ZENAIDA_DOMAIN_RENEW_YEARS)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if context.get('has_existing_order'):
            return shortcuts.redirect('billing_order_details', order_id=context.get('order').id)
        new_order = context.get('order')
        if new_order and new_order.total_price > new_order.owner.balance:
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(new_order.total_price - new_order.owner.balance)))
        return self.render_to_response(context)


class OrderDomainRestoreView(LoginRequiredMixin, TemplateView):
    template_name = 'billing/order_details.html'

    @create_or_update_single_order(item_type='domain_restore', item_price=settings.ZENAIDA_DOMAIN_RESTORE_PRICE)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'order': kwargs.get('order')})
        context['domain_expiry_date'] = timezone.now() + relativedelta(years=settings.ZENAIDA_DOMAIN_RENEW_YEARS)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if context.get('has_existing_order'):
            return shortcuts.redirect('billing_order_details', order_id=context.get('order').id)
        new_order = context.get('order')
        if new_order and new_order.total_price > new_order.owner.balance:
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(new_order.total_price - new_order.owner.balance)))
        return self.render_to_response(context)


class OrderCreateView(LoginRequiredMixin, CreateView):
    error_message = 'No domains were selected'

    def post(self, request, *args, **kwargs):
        # Check if there is already an order that started. If so, redirect user to that order.
        started_orders = orders.list_orders(
            owner=self.request.user,
            exclude_cancelled=True,
            include_statuses=['started']
        )
        if started_orders:
            messages.warning(self.request, 'There is an order you did not complete yet. '
                                           'Please confirm or cancel this order to create a new one')
            return shortcuts.redirect('billing_order_details', order_id=started_orders[0].id)

        order_items = request.POST.getlist('order_items')

        to_be_ordered = []
        for domain_name in order_items:
            domain_object = zdomains.domain_find(domain_name=domain_name)
            if not domain_object:
                raise Http404
            if domain_object.owner != request.user:
                logging.critical('user %r tried to make an order with domain from another owner' % request.user)
                raise SuspiciousOperation()
            try:
                item_type, item_price, item_name = orders.prepare_register_renew_restore_item(domain_object)
            except exceptions.DomainBlockedError as err:
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
        new_order = orders.order_multiple_items(
            owner=request.user,
            order_items=to_be_ordered,
        )
        if new_order.total_price > self.request.user.balance:
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(new_order.total_price - self.request.user.balance)))
        return shortcuts.render(request, 'billing/order_details.html', {'order': new_order})


class OrderDetailsView(LoginRequiredMixin, DetailView):
    template_name = 'billing/order_details.html'

    def get_object(self, queryset=None):
        return orders.get_order_by_id_and_owner(
            order_id=self.kwargs.get('order_id'), owner=self.request.user, log_action='check'
        )


class OrderExecuteView(LoginRequiredMixin, View):
    error_message_balance = 'Not enough funds on your balance to complete order. ' \
                            'Please buy more credits to be able to register/renew domains'
    error_message_technical = 'There is technical problem with order processing. ' \
                              'Please try again later.'
    success_message = 'Order processed successfully'
    processing_message = 'Order is processing, please wait'

    def _verify_existing_order(self, request, existing_order):
        for order_item_object in existing_order.items.all():
            if order_item_object.status in ['processed', 'pending', 'blocked', ]:
                continue
            target_domain = zdomains.domain_find(order_item_object.name)
            if not target_domain and order_item_object.type != 'domain_transfer':
                messages.error(request, 'One of the items is not valid anymore because related domain does not exist. Please start a new order.')
                return False
            if order_item_object.type == 'domain_renew':
                if not target_domain.contact_admin or not target_domain.contact_tech:
                    messages.error(request, 'Domain %s is missing a mandatory contact info. Please update domain info and confirm your order again.' % target_domain.name)
                    return False
        return True

    def post(self, request, *args, **kwargs):
        existing_order = orders.get_order_by_id_and_owner(
            order_id=kwargs.get('order_id'), owner=request.user, log_action='execute'
        )
        if existing_order.total_price > existing_order.owner.balance:
            messages.error(request, self.error_message_balance)
            return HttpResponseRedirect(shortcuts.resolve_url('billing_new_payment') + "?amount={}".format(
                int(existing_order.total_price - existing_order.owner.balance)))
        if not self._verify_existing_order(request, existing_order):
            return shortcuts.redirect('account_domains')
        new_status = orders.execute_order(existing_order)
        if new_status == 'processed':
            messages.success(request, self.success_message)
        elif new_status == 'processing':
            messages.success(request, self.processing_message)
        else:
            messages.error(request, self.error_message_technical)
        return shortcuts.redirect('account_domains')


class OrderCancelView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        existing_order = orders.get_order_by_id_and_owner(
            order_id=kwargs.get('order_id'), owner=request.user, log_action='cancel'
        )
        for order_item_object in existing_order.items.all():
            if order_item_object.type == 'domain_register':
                domain = zdomains.domain_find(domain_name=order_item_object.name)
                if domain and domain.status == 'inactive' and not domain.epp_id:
                    zdomains.domain_delete(domain_name=order_item_object.name)
        orders.cancel_and_remove_order(existing_order)
        messages.success(request, f'Order of {existing_order.description} is cancelled.')
        return shortcuts.redirect('billing_orders')
