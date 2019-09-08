import datetime

from dateutil.relativedelta import relativedelta
from django import shortcuts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView, CreateView, DeleteView, ListView, TemplateView, FormView

from back.models.domain import Domain
from back.models.contact import Contact
from back.models.profile import Profile
from base.exceptions import ExceededMaxAttemptsException
from base.bruteforceprotection import BruteForceProtection

from front import forms

from zen import zdomains
from zen import zcontacts
from zen import zzones
from zen import zmaster

from billing import orders


def validate_profile_and_contacts(dispatch_func):
    def dispatch_wrapper(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            if not request.user.profile.is_complete():
                messages.info(request, 'Please provide your contact information to be able to register new domains.')
                return shortcuts.redirect('account_profile')
            if len(zcontacts.list_contacts(request.user)) == 0:
                messages.info(request, 'Please create your first contact person and provide your contact information '
                                       'to be able to register new domains.')
                return shortcuts.redirect('account_contacts')
        return dispatch_func(self, request, *args, **kwargs)
    return dispatch_wrapper


class IndexPageView(TemplateView):
    template_name = 'base/index.html'

    @validate_profile_and_contacts
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

    @validate_profile_and_contacts
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return zdomains.list_domains(self.request.user.email)


class AccountDomainCreateView(FormView):
    template_name = 'front/account_domain_create.html'
    form_class = forms.DomainDetailsForm
    pk_url_kwarg = 'domain_name'
    success_message = 'New domain is added to your account, now click "Register" to confirm the order and activate it.'
    success_url = reverse_lazy('account_domains')

    @validate_profile_and_contacts
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'domain_name': self.kwargs.get('domain_name')})
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
        else:
            form_kwargs['initial']['contact_admin'] = self.request.user.contacts.all()[0]
            form_kwargs['initial']['contact_billing'] = self.request.user.contacts.all()[0]
            form_kwargs['initial']['contact_tech'] = self.request.user.contacts.all()[0]
        form_kwargs['current_user'] = self.request.user
        return form_kwargs

    def form_valid(self, form):
        domain_name = self.kwargs.get('domain_name')
        domain_tld = domain_name.split('.')[-1].lower()

        if not zzones.is_supported(domain_tld):
            messages.error(self.request, f'Domain zone "{domain_tld}" is not supported.')
            return shortcuts.redirect('account_domains')

        existing_domain = zdomains.domain_find(domain_name=domain_name)
        if existing_domain:
            if existing_domain.epp_id:
                # If domain has EPP id, it means that domain is already owned someone.
                messages.error(self.request, 'This domain is already registered.')
                return super().form_valid(form)
            if existing_domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
                # If domain was on someone's basket more than an hour, remove that from database in order to make it
                # available for current user.
                zdomains.domain_delete(domain_id=existing_domain.id)
            else:
                # If domain is on someone's basket, domain becomes unavailable.
                messages.warning(self.request, 'This domain is not available now.')
                return super().form_valid(form)

        domain_obj = form.save(commit=False)

        domain_creation_date = timezone.now()

        zdomains.domain_create(
            domain_name=domain_name,
            owner=self.request.user,
            create_date=domain_creation_date,
            expiry_date=domain_creation_date + relativedelta(years=2),
            registrant=zcontacts.get_registrant(self.request.user),
            contact_admin=domain_obj.contact_admin,
            contact_tech=domain_obj.contact_tech,
            contact_billing=domain_obj.contact_billing,
            nameservers=[
                domain_obj.nameserver1,
                domain_obj.nameserver2,
                domain_obj.nameserver3,
            ],
            save=True,
        )

        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AccountDomainUpdateView(UpdateView):
    template_name = 'front/account_domain_details.html'
    form_class = forms.DomainDetailsForm
    pk_url_kwarg = 'domain_id'
    success_message = 'Domain details successfully updated.'
    success_url = reverse_lazy('account_domains')

    @validate_profile_and_contacts
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
            domain_update = zmaster.domain_check_create_update_renew(
                domain_object=form.instance,
                sync_contacts=True,
                sync_nameservers=True,
                renew_years=None,
                save_to_db=False,
                raise_errors=False,
                log_events=True,
                log_transitions=True,
            )
            if not domain_update:
                messages.error(self.request, 'There were technical problems with domain info processing. '
                                             'Please try again later or contact customer support.')
                return super().form_valid(form)
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AccountDomainTransferCodeView(TemplateView):
    template_name = 'front/account_domain_transfer_code.html'

    @validate_profile_and_contacts
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        domain = shortcuts.get_object_or_404(Domain, pk=self.kwargs.get('domain_id'), owner=self.request.user)
        if not zmaster.domain_set_auth_info(domain):
            messages.error(self.request, 'There were technical problems with domain transfer code processing. '
                                         'Please try again later or contact customer support.')
            return shortcuts.redirect('account_domains')
        return self.render_to_response(self.get_context_data(transfer_code=domain.auth_key, domain_name=domain.name))


class AccountDomainTransferTakeoverView(FormView):

    template_name = 'front/account_domain_transfer_takeover.html'
    form_class = forms.DomainTransferTakeoverForm
    success_message = 'New domain will be added to your account after confirmation.'

    @validate_profile_and_contacts
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        domain_name = form.cleaned_data.get('domain_name').strip()
        transfer_code = form.cleaned_data.get('transfer_code').strip()
        info = zmaster.domain_read_info(
            domain=domain_name,
            auth_info=transfer_code,
        )
        if not info:
            messages.warning(self.request, 'Domain is not registered.')
            return super().form_invalid(form)
        current_registrar = info['epp']['response']['resData']['infData']['clID']
        if current_registrar == settings.ZENAIDA_REGISTRAR_ID:
            messages.warning(self.request, 'Domain transfer is not possible')
            return super().form_invalid(form)
        current_statuses = info['epp']['response']['resData']['infData']['status']
        current_statuses = [current_statuses, ] if not isinstance(current_statuses, list) else current_statuses
        current_statuses = [s['@s'] for s in current_statuses]
        if 'clientTransferProhibited' in current_statuses or 'serverTransferProhibited' in current_statuses:
            messages.error(self.request, 'Domain transfer is not possible at the moment. ' \
                                         'Please contact customer support.')
            return super().form_invalid(form)
        if len(orders.find_pending_domain_transfer_order_items(domain_name)):
            messages.warning(self.request, 'Domain transfer in progress')
            return super().form_invalid(form)
        current_registrar = info['epp']['response']['resData']['infData']['clID']
        if current_registrar == 'auction':
            price = 0.0
        else:
            price = 100.0
        transfer_order = orders.order_single_item(
            owner=self.request.user,
            item_type='domain_transfer',
            item_price=price,
            item_name=domain_name,
            item_details={
                'transfer_code': transfer_code,
                'rewrite_contacts': form.cleaned_data.get('rewrite_contacts'),
            },
        )
        messages.success(self.request, self.success_message)
        return shortcuts.redirect('billing_order_details', order_id=transfer_order.id)


class AccountProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'front/account_profile.html'
    model = Profile
    form_class = forms.AccountProfileForm
    error_message = 'There were technical problems with contact details processing. ' \
                    'Please try again later or contact customer support.'
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

        existing_registrant = zcontacts.get_registrant(self.request.user)
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

        if existing_registrant and existing_contacts:
            messages.success(self.request, 'Your profile information was successfully updated.')
        else:
            messages.success(
                self.request,
                'Your profile information was successfully updated, you can register new domains now.'
            )
        return super().form_valid(form)


class AccountContactCreateView(LoginRequiredMixin, CreateView):
    template_name = 'front/account_contact_create.html'
    form_class = forms.ContactPersonForm
    error_message = 'There were technical problems with contact details processing. ' \
                    'Please try again later or contact customer support.'
    success_message = 'New contact person successfully created.'
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
    template_name = 'front/account_contact_edit.html'
    model = Contact
    form_class = forms.ContactPersonForm
    pk_url_kwarg = 'contact_id'
    error_message = 'There were technical problems with contact details processing. ' \
                    'Please try again later or contact customer support.'
    success_message = 'Contact person details successfully updated.'
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
    success_message = 'Contact person successfully deleted.'
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

    def _get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def form_valid(self, form):
        result = None
        if settings.BRUTE_FORCE_PROTECTION_ENABLED:
            client_ip = self._get_client_ip()
            brute_force = BruteForceProtection(
                cache_key_prefix=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_KEY_PREFIX,
                key=client_ip,
                max_attempts=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_MAX_ATTEMPTS,
                timeout=settings.BRUTE_FORCE_PROTECTION_DOMAIN_LOOKUP_TIMEOUT
            )
            try:
                brute_force.register_attempt()
            except ExceededMaxAttemptsException:
                messages.error(self.request, 'Too many attempts, please try again later.')
                return super().form_valid(form)

        domain_name = form.cleaned_data.get('domain_name')

        if domain_name:
            if not zdomains.is_valid(domain_name):
                messages.error(self.request, 'Domain name is not valid')
                return super().form_valid(form)
            domain_tld = domain_name.split('.')[-1].lower()
            if not zzones.is_supported(domain_tld):
                messages.error(self.request, f'Domain zone "{domain_tld}" is not supported.')
                return super().form_valid(form)
            domain_available = zdomains.is_domain_available(domain_name)
            if domain_available:
                check_result = zmaster.domains_check(domain_names=[domain_name, ], )
                if check_result is None:
                    result = 'error'
                else:
                    if check_result.get(domain_name):
                        result = 'exist'
                    else:
                        result = 'not exist'
            else:
                result = 'exist'
        return self.render_to_response(self.get_context_data(form=form, domain_name=domain_name, result=result))
