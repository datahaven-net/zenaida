import datetime
import logging

from dateutil.relativedelta import relativedelta  # @UnresolvedImport

from django import shortcuts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic import UpdateView, CreateView, DeleteView, ListView, TemplateView, FormView


from back.models.domain import Domain
from back.models.contact import Contact
from back.models.profile import Profile

from front import forms
from front.decorators import validate_profile_exists, brute_force_protection

from epp import rpc_error

from zen import zdomains
from zen import zcontacts
from zen import zzones
from zen import zmaster

from billing import orders

logger = logging.getLogger(__name__)


class IndexPageView(TemplateView):
    template_name = 'base/index.html'

    @validate_profile_exists
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['total_domains'] = len(self.request.user.domains.all())
        return context


class AccountDomainsListView(ListView):
    template_name = 'front/account_domains.html'
    paginate_by = 10

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return zdomains.list_domains(self.request.user.email)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zmaster.domains_quick_sync(
            domain_objects_list=context.get('object_list', []),
            hours_passed=12,
            request_time_limit=3,
        )
        return context


class AccountDomainCreateView(FormView):
    template_name = 'front/account_domain_create.html'
    form_class = forms.DomainDetailsForm
    pk_url_kwarg = 'domain_name'
    success_message = 'Please confirm the payment to finish registering your domain.'
    success_url = reverse_lazy('account_domains')

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'domain_name': zdomains.clean_domain_name(self.kwargs.get('domain_name', ''))})
        context.update({'person_name': self.request.user.registrants.all()[0].person_name})
        return context

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        last_registered_domain = zdomains.get_last_registered_domain(self.request.user.email)
        if last_registered_domain:
            form_kwargs['initial']['contact_admin'] = last_registered_domain.contact_admin
            form_kwargs['initial']['contact_billing'] = last_registered_domain.contact_admin
            form_kwargs['initial']['contact_tech'] = last_registered_domain.contact_admin
            form_kwargs['initial']['nameserver1'] = last_registered_domain.nameserver1
            form_kwargs['initial']['nameserver2'] = last_registered_domain.nameserver2
            form_kwargs['initial']['nameserver3'] = last_registered_domain.nameserver3
            form_kwargs['initial']['nameserver4'] = last_registered_domain.nameserver4
        else:
            if self.request.user.contacts.first():
                form_kwargs['initial']['contact_admin'] = self.request.user.contacts.all()[0]
                form_kwargs['initial']['contact_billing'] = self.request.user.contacts.all()[0]
                form_kwargs['initial']['contact_tech'] = self.request.user.contacts.all()[0]
        form_kwargs['current_user'] = self.request.user
        return form_kwargs

    def form_valid(self, form):
        domain_name = zdomains.clean_domain_name(self.kwargs.get('domain_name', ''))
        if not zdomains.is_valid(domain_name):
            messages.error(self.request, 'Domain name is not valid')
            return self.render_to_response(self.get_context_data(form=form))

        domain_tld = domain_name.split('.')[-1]

        if not zzones.is_supported(domain_tld):
            messages.error(self.request, f'Domain zone "{domain_tld}" is not supported')
            return shortcuts.redirect('account_domains')

        existing_domain = zdomains.domain_find(domain_name=domain_name)
        if existing_domain:
            if existing_domain.epp_id:
                # If domain has EPP id, it means that domain is already owned by someone.
                messages.error(self.request, 'Domain name already registered')
                return super().form_valid(form)
            if existing_domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
                # If domain was on someone's basket more than an hour, remove that from database in order to make it
                # available for current user.
                zdomains.domain_delete(domain_id=existing_domain.id)
            else:
                # If domain is on someone's basket, domain becomes unavailable.
                messages.warning(self.request, 'Domain name is not available at the moment')
                return super().form_valid(form)

        domain_obj = form.save(commit=False)

        for nameserver in domain_obj.list_nameservers():
            if nameserver.strip().lower().endswith(domain_name):
                messages.error(self.request, f'Please use another nameserver instead of {nameserver}, "glue" records are not supported yet.')
                return super().form_valid(form)

        check_result = zmaster.domains_check(domain_names=[domain_name, ], )
        if check_result is None:
            messages.error(self.request, mark_safe('Service is unavailable at this moment. <br /> Please try again later.'))
            return super().form_valid(form)
        if check_result == 'non-supported-zone':
            messages.error(self.request, 'Domain zone is not supported')
            return super().form_valid(form)
        if isinstance(check_result.get(domain_name), Exception):
            messages.error(self.request, mark_safe('Domain is locked or service is unavailable at this moment. <br /> Please try again later.'))
            return super().form_valid(form)
        if check_result.get(domain_name) is True:
            messages.warning(self.request, mark_safe(f'<b>{domain_name}</b> is already registered.'))
            return super().form_valid(form)

        domain_creation_date = timezone.now()

        zdomains.domain_create(
            domain_name=domain_name,
            owner=self.request.user,
            create_date=domain_creation_date,
            expiry_date=domain_creation_date + relativedelta(years=settings.ZENAIDA_DOMAIN_RENEW_YEARS),
            registrant=zcontacts.get_oldest_registrant(self.request.user),
            contact_admin=domain_obj.contact_admin,
            contact_tech=domain_obj.contact_tech,
            contact_billing=domain_obj.contact_billing,
            nameservers=[
                domain_obj.nameserver1,
                domain_obj.nameserver2,
                domain_obj.nameserver3,
                domain_obj.nameserver4,
            ],
            save=True,
        )

        messages.success(self.request, self.success_message)
        return shortcuts.redirect('billing_order_register', domain_name=domain_name)


class AccountDomainUpdateView(UpdateView):
    template_name = 'front/account_domain_details.html'
    form_class = forms.DomainDetailsForm
    pk_url_kwarg = 'domain_id'
    success_message = 'Domain details successfully updated'
    success_url = reverse_lazy('account_domains')

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['current_user'] = self.request.user
        return form_kwargs

    def get_object(self, queryset=None):
        return shortcuts.get_object_or_404(Domain, pk=self.kwargs.get('domain_id'), owner=self.request.user)

    def form_valid(self, form):
        if form.instance.epp_id:
            outputs = zmaster.domain_check_create_update_renew(
                domain_object=form.instance,
                sync_contacts=True,
                sync_nameservers=True,
                renew_years=None,
                save_to_db=False,
                raise_errors=False,
                return_outputs=True,
                log_events=True,
                log_transitions=True,
            )
            if not outputs:
                messages.error(self.request, 'Domain details was not updated due to a technical problem. Please try again later.')
                return super().form_invalid(form)

            if outputs[-1] is True:
                messages.success(self.request, self.success_message)
                return super().form_valid(form)

            if isinstance(outputs[-1], (
                rpc_error.EPPCommandUseError,
                rpc_error.EPPCommandFailed,
                rpc_error.EPPBadResponse,
            )):
                messages.error(self.request, 'Domain details was not updated due to a technical problem. Please try again later.')
                return super().form_invalid(form)

            messages.error(self.request, 'Domain details was not updated due to incorrect field input.')
            return super().form_invalid(form)

        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AccountDomainTransferCodeView(TemplateView):
    template_name = 'front/account_domain_transfer_code.html'

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        domain = shortcuts.get_object_or_404(Domain, pk=self.kwargs.get('domain_id'), owner=self.request.user)
        if not zmaster.domain_set_auth_info(domain):
            messages.error(self.request, 'There is a technical problem with domain transfer code processing, '
                                         'please try again later')
            return shortcuts.redirect('account_domains')
        return self.render_to_response(self.get_context_data(transfer_code=domain.auth_key, domain_name=domain.name.strip().lower()))


class AccountDomainTransferTakeoverView(FormView):

    template_name = 'front/account_domain_transfer_takeover.html'
    form_class = forms.DomainTransferTakeoverForm
    success_message = 'New domain will be added to your account after confirmation'

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @brute_force_protection(
        cache_key_prefix=settings.BRUTE_FORCE_PROTECTION_DOMAIN_TRANSFER_KEY_PREFIX,
        max_attempts=settings.BRUTE_FORCE_PROTECTION_DOMAIN_TRANSFER_MAX_ATTEMPTS,
        timeout=settings.BRUTE_FORCE_PROTECTION_DOMAIN_TRANSFER_TIMEOUT
    )
    def form_valid(self, form):
        if self.request.temporarily_blocked:
            messages.error(self.request, 'Too many attempts made, please try again later')
            return self.render_to_response(self.get_context_data(form=form))

        domain_name = zdomains.clean_domain_name(form.cleaned_data.get('domain_name'))
        if not zdomains.is_valid(domain_name):
            messages.error(self.request, 'Domain name is not valid')
            return self.render_to_response(self.get_context_data(form=form))

        transfer_code = form.cleaned_data.get('transfer_code').strip()
        internal = False  # detects if transfer is going to happen within same registrar

        outputs = zmaster.domain_read_info(
            domain=domain_name,
            auth_info=transfer_code,
            return_outputs=True,
        )

        if not outputs:
            messages.warning(self.request, 'Domain name is not registered or transfer is not possible at the moment')
            return super().form_invalid(form)

        if isinstance(outputs[-1], rpc_error.EPPAuthorizationError):
            if outputs[-1].message.lower().count('incorrect authcode provided'):
                messages.error(self.request, 'Incorrect authorization code provided')
            else:
                messages.error(self.request, 'You are not authorized to transfer this domain')
            return super().form_invalid(form)

        if isinstance(outputs[-1], rpc_error.EPPObjectNotExist):
            messages.error(self.request, 'Domain name is not registered')
            return super().form_invalid(form)

        if isinstance(outputs[-1], rpc_error.EPPError):
            messages.error(self.request, 'Domain transfer failed due to unexpected error, please try again later')
            return super().form_invalid(form)

        if not outputs[-1].get(domain_name):
            messages.warning(self.request, 'Domain name is not registered')
            return super().form_invalid(form)

        if len(outputs) < 2:
            messages.error(self.request, 'Domain name transfer is not possible at the moment, please try again later')
            return super().form_invalid(form)

        info = outputs[-2]
        current_registrar = info['epp']['response']['resData']['infData']['clID']
        if current_registrar == settings.ZENAIDA_REGISTRAR_ID:
            internal = True
        current_statuses = info['epp']['response']['resData']['infData']['status']
        current_statuses = [current_statuses, ] if not isinstance(current_statuses, list) else current_statuses
        current_statuses = [s['@s'] for s in current_statuses]

        if info['epp']['response']['resData']['infData']['authInfo']['pw'] != 'Authinfo Correct':
            messages.error(self.request, 'Given transfer code is not correct')
            return super().form_invalid(form)

        if 'clientTransferProhibited' in current_statuses or 'serverTransferProhibited' in current_statuses:
            messages.error(self.request, 'Transfer failed. Probably the domain is locked or the Auth Code was wrong')
            return super().form_invalid(form)

        if len(orders.find_pending_domain_transfer_order_items(domain_name)):
            messages.warning(self.request, 'Domain transfer is already in progress')
            return super().form_invalid(form)

        if current_registrar in [settings.ZENAIDA_AUCTION_REGISTRAR_ID, settings.ZENAIDA_REGISTRAR_ID]:
            price = 0.0
        else:
            price = settings.ZENAIDA_DOMAIN_PRICE

        transfer_order = orders.order_single_item(
            owner=self.request.user,
            item_type='domain_transfer',
            item_price=price,
            item_name=domain_name,
            item_details={
                'transfer_code': transfer_code,
                'rewrite_contacts': True,
                'internal': internal,
            },
        )
        messages.success(self.request, self.success_message)
        return shortcuts.redirect('billing_order_details', order_id=transfer_order.id)


class AccountProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'front/account_profile.html'
    model = Profile
    form_class = forms.AccountProfileForm
    error_message = 'There is a technical problem with contact details processing, ' \
                    'please try again later'
    success_url = reverse_lazy('account_profile')

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        existing_contacts = zcontacts.list_contacts(self.request.user)
        if not existing_contacts:
            new_contact = zcontacts.contact_create_from_profile(self.request.user, form.instance)
            if not zmaster.contact_create_update(new_contact):
                messages.error(self.request, self.error_message)
                return HttpResponseRedirect(self.request.path_info)

        existing_registrant = zcontacts.get_oldest_registrant(self.request.user)
        if not existing_registrant:
            new_registrant = zcontacts.registrant_create_from_profile(self.request.user, form.instance)
            if not zmaster.contact_create_update(new_registrant):
                messages.error(self.request, self.error_message)
                return HttpResponseRedirect(self.request.path_info)
        else:
            zcontacts.registrant_update_from_profile(existing_registrant, form.instance)
            if not zmaster.contact_create_update(existing_registrant):
                messages.error(self.request, self.error_message)
                return HttpResponseRedirect(self.request.path_info)

        if existing_registrant:
            messages.success(self.request, 'Your profile information was successfully updated')
        else:
            messages.success(
                self.request,
                'Profile information successfully updated, you can register new domains now'
            )
        return super().form_valid(form)


class AccountContactCreateView(LoginRequiredMixin, CreateView):
    template_name = 'front/account_contact_create_update.html'
    form_class = forms.ContactPersonForm
    error_message = 'There is a technical problem with contact details processing, ' \
                    'please try again later'
    success_message = 'New contact person successfully created'
    success_url = reverse_lazy('account_contacts')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.owner = self.request.user
        if not zmaster.contact_create_update(self.object):
            messages.error(self.request, self.error_message)
            return HttpResponseRedirect(self.request.path_info)

        self.object.save()
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AccountContactUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'front/account_contact_create_update.html'
    model = Contact
    form_class = forms.ContactPersonForm
    pk_url_kwarg = 'contact_id'
    error_message = 'There is a technical problem with contact details processing, ' \
                    'please try again later'
    success_message = 'Contact person details successfully updated'
    success_url = reverse_lazy('account_contacts')

    def get_object(self, queryset=None):
        return shortcuts.get_object_or_404(Contact, pk=self.kwargs.get('contact_id'), owner=self.request.user)

    def form_valid(self, form):
        if not zmaster.contact_create_update(form.instance):
            messages.error(self.request, self.error_message)
            return HttpResponseRedirect(self.request.path_info)
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AccountContactDeleteView(LoginRequiredMixin, DeleteView):
    template_name = 'front/account_contact_delete.html'
    model = Contact
    pk_url_kwarg = 'contact_id'
    success_message = 'Contact person successfully removed'
    success_url = reverse_lazy('account_contacts')

    def get_object(self, queryset=None):
        return shortcuts.get_object_or_404(Contact, pk=self.kwargs.get('contact_id'), owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


class AccountContactsListView(LoginRequiredMixin, ListView):
    template_name = 'front/account_contacts.html'
    model = Contact
    paginate_by = 10

    def get_queryset(self):
        return zcontacts.list_contacts(self.request.user)


class DomainLookupView(FormView):
    template_name = 'front/domain_lookup.html'
    form_class = forms.DomainLookupForm
    success_url = reverse_lazy('domain_lookup')

    @brute_force_protection(
        cache_key_prefix=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_KEY_PREFIX,
        max_attempts=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_MAX_ATTEMPTS,
        timeout=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_TIMEOUT
    )
    def form_valid(self, form):
        if self.request.temporarily_blocked:
            messages.error(self.request, 'Too many attempts made, please try again later')
            return super().form_valid(form)
        result = None

        domain_name = zdomains.clean_domain_name(form.cleaned_data.get('domain_name'))

        if domain_name:
            if not zdomains.is_valid(domain_name):
                messages.error(self.request, 'Domain name is not valid')
                return self.render_to_response(self.get_context_data(form=form, domain_name=domain_name, result=result))
            domain_tld = domain_name.split('.')[-1].lower()
            if not zzones.is_supported(domain_tld):
                messages.error(self.request, f'Domain zone "{domain_tld}" is not supported')
                return self.render_to_response(self.get_context_data(form=form, domain_name=domain_name, result=result))
            domain_available = zdomains.is_domain_available(domain_name)
            if domain_available:
                check_result = zmaster.domains_check(domain_names=[domain_name, ], )
                if check_result is None:
                    messages.error(self.request, mark_safe('Service is unavailable at this moment. <br /> Please try again later.'))
                elif check_result == 'non-supported-zone':
                    messages.error(self.request, 'Domain zone is not supported')
                else:
                    if isinstance(check_result.get(domain_name), Exception):
                        messages.error(self.request, mark_safe('Service is unavailable at this moment. <br /> Please try again later.'))
                    else:
                        if check_result.get(domain_name) is True:
                            messages.warning(self.request, mark_safe(f'<b>{domain_name}</b> is already registered.'))
                        else:
                            result = 'not exist'
            else:
                messages.warning(self.request, mark_safe(f'<b>{domain_name}</b> is already registered.'))
        return self.render_to_response(self.get_context_data(form=form, domain_name=domain_name, result=result))


class EPPStatusView(TemplateView):
    template_name = 'base/epp_status.html'
    cache_key = 'zenaida-epp-health-status'

    def check_epp_status(self):
        try:
            from epp import rpc_client
            rpc_client.cmd_domain_check(
                domains=[settings.ZENAIDA_GATE_HEALTH_CHECK_DOMAIN_NAME, ],
                raise_for_result=True,
                request_time_limit=15,
            )
        except Exception as exc:
            logger.exception('EPP health check failed')
            return str(exc)
        return 'OK'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        try:
            latest_status = cache.get(self.cache_key)
        except:
            latest_status = None
        if not latest_status:
            latest_status = self.check_epp_status()
            if latest_status == 'OK':
                cache.set(self.cache_key, latest_status, timeout=settings.ZENAIDA_GATE_HEALTH_CHECK_PERIOD)
        context.update({'epp': latest_status, })
        if latest_status != 'OK':
            logger.critical('EPP status is: %r', latest_status)
            return HttpResponseServerError(content=latest_status)
        return self.render_to_response(context)


def handler404(request, exception, template_name="front/404_error.html"):
    response = render(request, template_name)
    response.status_code = 404
    return response


def handler500(request, template_name="front/500_error.html"):
    response = render(request, template_name)
    response.status_code = 500
    return response
