import datetime

from django import shortcuts
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

from front import forms, helpers

from zen import zdomains
from zen import zcontacts
from zen import zzones
from zen import zmaster


class IndexPageView(TemplateView):
    template_name = 'base/index.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if not request.user.profile.is_complete():
                return shortcuts.redirect('account_profile')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['total_domains'] = len(self.request.user.domains.all())
        return context


class AccountDomainsListView(ListView):
    template_name = 'front/account_domains.html'
    paginate_by = 10

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_complete():
            messages.info(request, 'Please provide your contact information to be able to register new domains.')
            return shortcuts.redirect('account_profile')
        if len(zcontacts.list_contacts(request.user)) == 0:
            messages.info(request, 'Please create your first contact person and provide your contact information '
                                   'to be able to register new domains.')
            return shortcuts.redirect('account_contacts')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return zdomains.list_domains(self.request.user.email)


class AccountDomainCreateView(FormView):
    template_name = 'front/account_domain_create.html'
    form_class = forms.DomainDetailsForm
    pk_url_kwarg = 'domain_name'
    success_message = 'New domain is added to your account, now click "Register" to confirm the order and activate it.'
    success_url = reverse_lazy('account_domains')

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_complete():
            messages.info(request, 'Please provide your contact information to be able to register new domains.')
            return shortcuts.redirect('account_profile')
        if len(zcontacts.list_contacts(request.user)) == 0:
            messages.info(request, 'Please create your first contact person and provide your contact information '
                                   'to be able to register new domains.')
            return shortcuts.redirect('account_contacts')
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

        zdomains.domain_create(
            domain_name=domain_name,
            owner=self.request.user,
            create_date=timezone.now(),
            expiry_date=timezone.now() + datetime.timedelta(days=365),
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

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.profile.is_complete():
            messages.info(request, 'Please provide your contact information to be able to register new domains.')
            return shortcuts.redirect('account_profile')
        if len(zcontacts.list_contacts(request.user)) == 0:
            messages.info(request, 'Please create your first contact person and provide your contact information '
                                   'to be able to register new domains.')
            return shortcuts.redirect('account_contacts')
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


@login_required
def account_domain_transfer(request):
    domain = shortcuts.get_object_or_404(Domain, name=request.GET['domain_name'], owner=request.user)
    transfer_code = helpers.get_transfer_code()
    # TODO Send this code to the Cocca.
    return shortcuts.render(request, 'front/account_domain_transfer.html', {
        'transfer_code': transfer_code,
        'domain_name': domain.name,
    })


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


class DomainLookupView(TemplateView):
    template_name = 'front/domain_lookup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['result'] = None
        domain_name = self.request.GET.get('domain_name')
        context['domain_name'] = domain_name
        if domain_name:
            if not zdomains.is_valid(domain_name):
                messages.error(self.request, 'Domain name is not valid')
                return context
            domain_tld = domain_name.split('.')[-1].lower()
            if not zzones.is_supported(domain_tld):
                messages.error(self.request, f'Domain zone "{domain_tld}" is not supported.')
                return context
            domain_available = zdomains.is_domain_available(domain_name)
            if domain_available:
                check_result = zmaster.domains_check(domain_names=[domain_name, ], )
                if check_result is None:
                    context['result'] = 'error'
                else:
                    if check_result.get(domain_name):
                        context['result'] = 'exist'
                    else:
                        context['result'] = 'not exist'
            else:
                context['result'] = 'exist'
        return context
