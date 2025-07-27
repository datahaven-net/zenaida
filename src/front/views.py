import datetime
import logging

from dateutil.relativedelta import relativedelta  # @UnresolvedImport

from django import shortcuts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.views.generic import UpdateView, CreateView, DeleteView, ListView, TemplateView, FormView, RedirectView

from back.models.domain import Domain
from back.models.contact import Contact
from back.models.profile import Profile

from front import forms
from front.decorators import validate_profile_exists, brute_force_protection

from epp import rpc_error
from epp import rpc_client

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
        return zdomains.list_domains(self.request.user.email, domain_name_like=(self.request.GET.get("q") or None))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get("q") or ''
        domain_objects_list = context.get('object_list', [])
        if settings.ZENAIDA_SYNC_ACCOUNT_DOMAINS_LIST and len(domain_objects_list) < 10:
            zmaster.domains_quick_sync(
                domain_objects_list=domain_objects_list,
                hours_passed=12,
                request_time_limit=3,
            )
        return context


class AccountDomainCreateView(FormView):
    template_name = 'front/account_domain_create.html'
    form_class = forms.DomainCreateForm
    pk_url_kwarg = 'domain_name'
    success_message = 'Please confirm the payment to finish registering your domain'
    success_url = reverse_lazy('account_domains')

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'domain_name': zdomains.clean_domain_name(self.kwargs.get('domain_name', ''))})
        context.update({'person_name': self.request.user.registrants.all()[0].person_name})
        context.update({'duration_years': settings.ZENAIDA_DOMAIN_RENEW_YEARS})
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
            if existing_domain.create_date and (existing_domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow()):
                # If domain was on someone's basket more than an hour, remove that from database in order to make it
                # available for current user.
                zdomains.domain_delete(domain_id=existing_domain.id)
            else:
                # If domain is on someone's basket, domain becomes unavailable.
                messages.warning(self.request, 'Domain name is not available at the moment')
                return super().form_valid(form)

        domain_obj = form.save(commit=False)

        for nameserver in domain_obj.list_nameservers():
            if nameserver.strip() and nameserver.strip().lower().endswith(domain_name):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['domain_id'] = self.kwargs.get('domain_id')
        return context

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
                new_domain_statuses=form.epp_statuses,
                save_to_db=False,
                raise_errors=False,
                return_outputs=True,
                log_events=True,
                log_transitions=True,
            )
            if not outputs:
                messages.error(self.request, 'Domain details were not updated due to a technical problem. Please try again later.')
                return super().form_invalid(form)

            if outputs[-1] is True:
                messages.success(self.request, self.success_message)
                return super().form_valid(form)

            if isinstance(outputs[-1], (
                rpc_error.EPPCommandUseError,
                rpc_error.EPPCommandFailed,
                rpc_error.EPPBadResponse,
            )):
                messages.error(self.request, 'Domain details were not updated due to a technical problem. Please try again later.')
                return super().form_invalid(form)

            messages.error(self.request, 'Domain details were not updated due to incorrect field input.')
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
        messages.success(self.request, 'A new authorization code has been generated.'
                         'Please keep in mind that domain authorization change will take several minutes to complete.')
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
        if current_registrar.lower() == settings.ZENAIDA_REGISTRAR_ID.lower():
            internal = True
        current_statuses = info['epp']['response']['resData']['infData']['status']
        current_statuses = [current_statuses, ] if not isinstance(current_statuses, list) else current_statuses
        current_statuses = [s['@s'] for s in current_statuses]

        pw = info['epp']['response']['resData']['infData']['authInfo']['pw']
        if pw != 'Authinfo Correct' and pw != transfer_code:
            messages.error(self.request, 'Given transfer code is not correct')
            return super().form_invalid(form)

        if 'clientTransferProhibited' in current_statuses or 'serverTransferProhibited' in current_statuses:
            messages.error(self.request, 'Transfer failed. Probably the domain is locked or the Auth Code was wrong')
            return super().form_invalid(form)

        if len(orders.find_pending_domain_transfer_order_items(domain_name)):
            messages.warning(self.request, 'Domain transfer is already in progress')
            return super().form_invalid(form)

        if current_registrar.lower() in [settings.ZENAIDA_AUCTION_REGISTRAR_ID.lower(), settings.ZENAIDA_REGISTRAR_ID.lower()]:
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


class AccountDomainDSRecordsView(FormView):
    template_name = 'front/account_domain_ds_records.html'
    form_class = forms.DomainDSRecordForm
    pk_url_kwarg = 'domain_id'
    success_message = 'Delegation Signer information successfully updated'
    error_message = 'There is a technical problem with domain DNSSEC details processing, ' \
                    'please try again later'
    success_url = reverse_lazy('account_domains')

    @validate_profile_exists
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        domain = shortcuts.get_object_or_404(Domain, pk=kwargs['domain_id'], owner=request.user)
        self.kwargs['domain_name'] = domain.name
        try:
            epp_response = rpc_client.cmd_domain_info(
                domain=domain.name,
                raise_for_result=True,
            )
        except rpc_error.EPPError:
            logger.exception('domain EPP info read failed')
            messages.error(request, self.error_message)
            return shortcuts.redirect('account_domains')
        try:
            infData = (epp_response['epp']['response'].get('extension') or {}).get('infData') or {}
            dsData = infData.get('dsData') or []
            if not isinstance(dsData, list):
                dsData = [dsData, ]
            self.kwargs['ds_data'] = dsData
        except:
            logger.exception('domain EPP info parse error')
            messages.error(request, self.error_message)
            return shortcuts.redirect('account_domains')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        domain = shortcuts.get_object_or_404(Domain, pk=self.kwargs.get('domain_id'), owner=self.request.user)
        self.kwargs['domain_name'] = domain.name
        record_delete = request.POST.get('record_delete')
        if record_delete:
            try:
                epp_response = rpc_client.cmd_domain_info(
                    domain=domain.name,
                    raise_for_result=True,
                )
            except rpc_error.EPPError:
                logger.exception('domain EPP info read failed')
                messages.error(request, self.error_message)
                return shortcuts.redirect('account_domains')
            try:
                record_delete_index = int(record_delete.replace('record', ''))
                infData = (epp_response['epp']['response'].get('extension') or {}).get('infData') or {}
                dsData = infData.get('dsData') or []
                if not isinstance(dsData, list):
                    dsData = [dsData, ]
                self.kwargs['ds_data'] = dsData
                delete_ds_data = dsData[record_delete_index-1]
            except:
                logger.exception('domain EPP info parse error')
                messages.error(request, self.error_message)
                return shortcuts.redirect('account_domains')
            try:
                rem_secdns = dict(
                    key_tag=delete_ds_data.get('keyTag') or '',
                    alg=delete_ds_data.get('alg') or '',
                    digest_type=delete_ds_data.get('digestType') or '',
                    digest=delete_ds_data.get('digest') or '',
                )
                if 'keyData' in delete_ds_data:
                    rem_secdns.update(dict(
                        keydata_flags=(delete_ds_data.get('keyData') or {}).get('flags') or '',
                        keydata_protocol=(delete_ds_data.get('keyData') or {}).get('protocol') or '',
                        keydata_alg=(delete_ds_data.get('keyData') or {}).get('alg') or '',
                        keydata_pubkey=(delete_ds_data.get('keyData') or {}).get('pubKey') or '',
                    ))
                epp_delete_response = rpc_client.cmd_domain_update(
                    domain=domain.name,
                    rem_secdns=rem_secdns,
                    raise_for_result=True,
                )
            except rpc_error.EPPError:
                logger.exception('domain EPP info read failed')
                messages.error(request, self.error_message)
                return shortcuts.redirect('account_domains')
            logger.debug('EPP response: %r' % epp_delete_response)
            messages.success(self.request, self.success_message)
            return shortcuts.redirect('account_domain_edit', domain_id=domain.id)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        domain = shortcuts.get_object_or_404(Domain, pk=self.kwargs.get('domain_id'), owner=self.request.user)
        try:
            add_secdns = dict(
                key_tag=str(form.cleaned_data.get('key_tag')),
                alg=form.cleaned_data.get('alg').strip(),
                digest_type=form.cleaned_data.get('digest_type').strip(),
                digest=form.cleaned_data.get('digest').strip(),
            )
            if form.cleaned_data.get('keydata_pubkey').strip():
                add_secdns.update(dict(
                    keydata_flags=form.cleaned_data.get('keydata_flags').strip(),
                    keydata_protocol=form.cleaned_data.get('keydata_protocol').strip(),
                    keydata_alg=form.cleaned_data.get('keydata_alg').strip(),
                    keydata_pubkey=form.cleaned_data.get('keydata_pubkey').strip(),
                ))
            epp_add_response = rpc_client.cmd_domain_update(
                domain=domain.name,
                add_secdns=add_secdns,
                raise_for_result=True,
            )
        except rpc_error.EPPError:
            logger.exception('domain EPP info read failed')
            messages.error(self.request, self.error_message)
            return shortcuts.redirect('account_domains')
        logger.debug('EPP response: %r' % epp_add_response)
        messages.success(self.request, self.success_message)
        return shortcuts.redirect('account_domain_edit', domain_id=domain.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['domain_name'] = self.kwargs['domain_name']
        context['domain_id'] = self.kwargs['domain_id']
        context['key_tags'] = []
        context['forms'] = []
        for ds_index in range(len(self.kwargs['ds_data'])):
            ds = self.kwargs['ds_data'][ds_index]
            ds_form_data = dict(
                key_tag=ds.get('keyTag') or '',
                alg=ds.get('alg') or '',
                digest_type=ds.get('digestType') or '',
                digest=ds.get('digest') or '',
                keydata_flags=(ds.get('keyData') or {}).get('flags') or '',
                keydata_protocol=(ds.get('keyData') or {}).get('protocol') or '',
                keydata_alg=(ds.get('keyData') or {}).get('alg') or '',
                keydata_pubkey=(ds.get('keyData') or {}).get('pubKey') or '',
            )
            frm = forms.DomainDSRecordReadOnlyForm()
            frm.ds_id = 'record%d' % (1 + ds_index)
            for field_name in ds_form_data.keys():
                if field_name == 'alg':
                    ds_form_data[field_name] = dict((
                        (0, ''),
                        (1, '1: RSA/MD5 [RSAMD5]'),
                        (3, '3: DSA/SHA-1'),
                        (5, '5: RSA/SHA-1'),
                        (6, '6: DSA-NSEC3-SHA1'),
                        (7, '7: RSASHA1-NSEC3-SHA1'),
                        (8, '8: RSA/SHA-256'),
                        (10, '10: RSA/SHA-512'),
                        (12, '12: GOST R 34.10-2001'),
                        (13, '13: ECDSA/SHA-256'),
                        (14, '14: ECDSA/SHA-384'),
                        (15, '15: ED25519'),
                        (16, '16: ED448'),
                    )).get(int(ds_form_data[field_name] or 0))
                elif field_name == 'digest_type':
                    ds_form_data[field_name] = dict((
                        (0, ''),
                        (1, '1: SHA-1'),
                        (2, '2: SHA-256'),
                        (3, '3: GOST R 34.11-94'),
                        (4, '4: SHA-384'),
                    )).get(int(ds_form_data[field_name] or 0))
                elif field_name == 'keydata_alg':
                    ds_form_data[field_name] = dict((
                        (0, ''),
                        (1, '1: RSA/MD5 [RSAMD5]'),
                        (3, '3: DSA/SHA-1'),
                        (5, '5: RSA/SHA-1'),
                        (7, '7: RSASHA1-NSEC3-SHA1'),
                        (8, '8: RSA/SHA-256'),
                        (10, '10: RSA/SHA-512'),
                        (12, '12: GOST R 34.10-2001'),
                        (13, '13: ECDSA/SHA-256'),
                        (14, '14: ECDSA/SHA-384'),
                        (15, '15: ED25519'),
                        (16, '16: ED448'),
                    )).get(int(ds_form_data[field_name] or 0))
            frm.initial = ds_form_data
            context['forms'].append(frm)
            context['key_tags'].append(frm.ds_id)
        return context


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


class AccountProfileEmailTestView(LoginRequiredMixin, RedirectView):

    pattern_name = 'account_profile'

    def get_redirect_url(self, *args, **kwargs):
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = self.request.user.profile.contact_email
        context = {
            'subject': 'Service email test from %s' % settings.SITE_BASE_URL,
            'site_url': settings.SITE_BASE_URL,
        }
        email_template = 'email/test_email.html'
        html_content = render_to_string(email_template, context=context, request=None)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=context['subject'],
            body=text_content,
            from_email=from_email,
            to=[to_email, ],
            bcc=[to_email, ],
            cc=[to_email, ],
        )
        msg.attach_alternative(html_content, 'text/html')
        if msg.send():
            messages.add_message(self.request, messages.SUCCESS, 'A test email has been sent to your email address.')
        else:
            messages.add_message(self.request, messages.ERROR, 'A test email dispatch failed. Please contact system administrator.')
        return super().get_redirect_url()


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
                request_time_limit=60,
            )
        except Exception as exc:
            logger.exception('EPP health check failed')
            return str(exc)
        return 'OK'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        latest_status = None
        if settings.ZENAIDA_GATE_HEALTH_CACHE_ENABLED:
            try:
                latest_status = cache.get(self.cache_key)
            except Exception as exc:
                logger.exception('Reading cache key failed: %r', exc)
        if not latest_status:
            latest_status = self.check_epp_status()
            if latest_status == 'OK':
                if settings.ZENAIDA_GATE_HEALTH_CACHE_ENABLED:
                    try:
                        cache.set(self.cache_key, latest_status, timeout=settings.ZENAIDA_GATE_HEALTH_CHECK_PERIOD)
                    except Exception as exc:
                        logger.exception('Writing cache key failed: %r', exc)
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
