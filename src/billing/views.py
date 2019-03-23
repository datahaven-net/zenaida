import logging
import datetime

from django import shortcuts
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.core import exceptions
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import TemplateView, FormView, DetailView

from auth.views import BaseLoginRequiredMixin
from billing import forms as billing_forms
from billing import orders as billing_orders
from billing import payments
from billing.pay_4csonline  import views as pay_4csonline_views

from zen import zdomains


@login_required
def billing_overview(request):
    """
    """
    # TODO: this needs to be done
    pass


class NewPaymentView(FormView, BaseLoginRequiredMixin):
    template_name = 'billing/new_payment.html'
    form_class = billing_forms.NewPaymentForm
    error_message = 'Payment method is invalid'
    success_url = reverse_lazy('billing_new_payment')

    def form_valid(self, form):
        if not settings.BILLING_BYPASS_PAYMENT_TIME_CHECK:
            my_latest_payment = payments.latest_payment(self.request.user)
            if my_latest_payment:
                if timezone.now() - my_latest_payment.started_at < datetime.timedelta(minutes=3):
                    messages.info(self.request, 'Please wait few minutes and then try again.')
                    return shortcuts.redirect('billing_new_payment')

        new_payment = payments.start_payment(
            owner=self.request.user,
            amount=form.cleaned_data['amount'],
            payment_method=form.cleaned_data['payment_method'],

        )

        if new_payment.method == 'pay_4csonline':
            return pay_4csonline_views.start_payment(self.request, transaction_id=new_payment.transaction_id)
        messages.error(self.request, self.error_message)
        return super().form_valid(form)


@login_required
def orders_list(request):
    """
    """
    if request.method == 'POST':
        form = billing_forms.FilterOrdersByDateForm(request.POST)
        order_objects = billing_orders.list_orders_by_date(
            owner=request.user,
            year=form.data.get('year'),
            month=form.data.get('month'),
            exclude_cancelled=True,
        )
    else:
        form = billing_forms.FilterOrdersByDateForm()
        order_objects = billing_orders.list_orders(owner=request.user, exclude_cancelled=True)
    page = request.GET.get('page', 1)
    paginator = Paginator(order_objects, 10)
    try:
        order_objects = paginator.page(page)
    except PageNotAnInteger:
        order_objects = paginator.page(1)
    except EmptyPage:
        order_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
        'form': form,
    })


@login_required
def payments_list(request):
    """
    """
    payment_objects = payments.list_payments(owner=request.user, statuses=['processed', ])
    page = request.GET.get('page', 1)
    paginator = Paginator(payment_objects, 10)
    try:
        payment_objects = paginator.page(page)
    except PageNotAnInteger:
        payment_objects = paginator.page(1)
    except EmptyPage:
        payment_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(request, 'billing/account_payments.html', {
        'objects': payment_objects,
    })


class OrderDomainRegisterView(TemplateView, BaseLoginRequiredMixin):
    template_name = 'billing/order_details.html'
    error_message = 'You don\'t have enough credits to register a domain.'

    def dispatch(self, request, *args, **kwargs):
        if request.user.balance < 100:
            messages.error(request, self.error_message)
            return shortcuts.redirect('billing_new_payment')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        new_order = billing_orders.order_single_item(
            owner=self.request.user,
            item_type='domain_register',
            item_price=100.0,
            item_name=kwargs.get('domain_name'),
        )
        context.update({'order': new_order})
        return context


class OrderDomainRenewView(TemplateView, BaseLoginRequiredMixin):
    template_name = 'billing/order_details.html'
    error_message = 'You don\'t have enough credits to renew a domain.'

    def dispatch(self, request, *args, **kwargs):
        if request.user.balance < 100:
            messages.error(request, self.error_message)
            return shortcuts.redirect('billing_new_payment')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        renewal_order = billing_orders.order_single_item(
            owner=self.request.user,
            item_type='domain_renew',
            item_price=100.0,
            item_name=kwargs.get('domain_name'),
        )
        context.update({'order': renewal_order})
        return context


@login_required
def order_domain_restore(request):
    """
    """
    # TODO: this needs to be done
    pass


@login_required
def order_create(request):
    """
    """
    order_items = request.POST.getlist('order_items')
    to_be_ordered = []
    for domain_name in order_items:
        domain_object = zdomains.domain_find(domain_name=domain_name)
        if not domain_object:
            raise ValueError()
        if domain_object.owner != request.user:
            logging.critical('User %s tried to make an order with domain from another owner' % request.user)
            raise exceptions.SuspiciousOperation()
        item_type = 'domain_register'
        if domain_object.can_be_restored:
            item_type = 'domain_restore'
        elif domain_object.is_registered:
            item_type = 'domain_renew'
        to_be_ordered.append(dict(
            item_type=item_type,
            item_price=100.0,
            item_name=domain_object.name,
        ))
    if not to_be_ordered:
        messages.error(request, 'No domains were selected.')
        return shortcuts.redirect('billing_orders')
    new_order = billing_orders.order_multiple_items(
        owner=request.user,
        order_items=to_be_ordered,
    )
    return shortcuts.render(request, 'billing/order_details.html', {
        'order': new_order,
    }, )


class OrderDetailsView(DetailView, BaseLoginRequiredMixin):
    template_name = 'billing/order_details.html'

    def get_object(self, queryset=None):
        return billing_orders.get_order_by_id_and_owner(
            order_id=self.kwargs.get('order_id'), owner=self.request.user, log_action='check'
        )


@login_required
def order_execute(request, order_id):
    """
    """
    existing_order = billing_orders.get_order_by_id_and_owner(
        order_id=order_id, owner=request.user, log_action='execute'
    )
    if existing_order.total_price > existing_order.owner.balance:
        messages.error(request, 'Not enough funds on your balance to complete order. Please buy more credits to be able to register/renew domains.')
        return shortcuts.redirect('billing_orders')
    if billing_orders.execute_single_order(existing_order):
        messages.success(request, 'Order processed successfully.')
    else:
        messages.error(request, 'There were technical problems with order processing. '
                                                      'Please try again later or contact customer support.')
    return shortcuts.redirect('billing_orders')


@login_required
def order_cancel(request, order_id):
    """
    """
    existing_order = billing_orders.get_order_by_id_and_owner(
        order_id=order_id, owner=request.user, log_action='cancel'
    )
    billing_orders.cancel_single_order(existing_order)
    messages.success(request, 'Order of %s cancelled.' % existing_order.description)
    return shortcuts.redirect('billing_orders')


@login_required
def orders_modify(request):
    order_objects = billing_orders.list_orders(owner=request.user)
    name = request.POST.get('name')

    return shortcuts.render(request, 'billing/account_orders.html', {
        'objects': order_objects,
    }, )


@login_required
def order_receipt_download(request, order_id=None):
    """
    """
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if order_id:
        pdf_info = billing_orders.build_receipt(
            owner=request.user,
            order_id=order_id,
        )
    else:
        pdf_info = billing_orders.build_receipt(
            owner=request.user,
            year=request.GET.get('year'),
            month=request.GET.get('month'),
        )
    if not pdf_info:
        return shortcuts.redirect('billing_orders')
    response = HttpResponse(pdf_info['body'], content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={pdf_info["filename"]}'
    return response


@login_required
def domain_get_auth_code(request):
    """
    """
    # TODO: this needs to be done
    pass
