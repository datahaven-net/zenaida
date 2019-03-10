import datetime

from django import shortcuts
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView, CreateView, DeleteView, ListView

from auth.views import BaseLoginRequiredMixin
from back.models.domain import Domain
from back.models.contact import Contact
from back.models.profile import Profile

from front import forms, helpers

from zen import zdomains
from zen import zcontacts
from zen import zzones
from zen import zmaster


def index_page(request):
    if not request.user.is_authenticated:
        return shortcuts.render(request, 'base/index.html')
    if not request.user.profile.is_complete():
        return shortcuts.redirect('account_profile')
    return shortcuts.render(request, 'base/index.html', {
        'total_domains': len(request.user.domains.all()),
    })


@login_required
def account_domains(request):
    if not request.user.profile.is_complete():
        messages.info(request, 'Please provide your contact information to be able to register new zdomains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(zcontacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new zdomains.')
        # return account_contacts(request)
        return shortcuts.redirect('account_contacts')
    domain_objects = zdomains.list_domains(request.user.email)
    if not domain_objects:
        return domain_lookup(request)
    page = request.GET.get('page', 1)
    paginator = Paginator(domain_objects, 10)
    try:
        domain_objects = paginator.page(page)
    except PageNotAnInteger:
        domain_objects = paginator.page(1)
    except EmptyPage:
        domain_objects = paginator.page(paginator.num_pages)
    return shortcuts.render(request, 'front/account_domains.html', {
        'objects': domain_objects,
    })


@login_required
def account_domain_create(request):
    if not request.user.profile.is_complete():
        messages.info(request, 'Please provide your contact information to be able to register new zdomains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(zcontacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new zdomains.')
        # return account_contacts(request)
        return shortcuts.redirect('account_contacts')
    if request.method != 'POST':
        form = forms.DomainDetailsForm(current_user=request.user)
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    form = forms.DomainDetailsForm(current_user=request.user, data=request.POST)
    domain_name = request.GET['domain_name']
    domain_tld = domain_name.split('.')[-1].lower()
    if not zzones.is_supported(domain_tld):
        messages.error(request, 'Domain zone ".%s" is not supported by that server.' % domain_tld)
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    domain_obj = form.save(commit=False)
    existing_domain = zdomains.find(domain_name=domain_name)
    if existing_domain:
        if existing_domain.epp_id:
            messages.error(request, 'This domain is already registered.')
            return shortcuts.render(request, 'front/account_domain_details.html', {
                'form': form,
            })
        if existing_domain.create_date.replace(tzinfo=None) + datetime.timedelta(hours=1) < datetime.datetime.utcnow():
            zdomains.delete(domain_id=existing_domain.id)
        else:
            messages.warning(request, 'This domain is not available now.')
            return shortcuts.render(request, 'front/account_domain_details.html', {
                'form': form,
            })
    zdomains.create(
        domain_name=domain_name,
        owner=request.user,
        create_date=timezone.now(),
        expiry_date=timezone.now() + datetime.timedelta(days=365),
        registrant=zcontacts.get_registrant(request.user),
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
    messages.success(request, 'New domain was added to your account, now click "Register" to confirm the order and activate it.')
    return shortcuts.redirect('account_domains')


@login_required
def account_domain_edit(request, domain_id):
    if not request.user.profile.is_complete():
        messages.info(request, 'Please provide your contact information to be able to register new zdomains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(zcontacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new zdomains.')
        # return account_contacts(request)
        return shortcuts.redirect('account_contacts')
    domain_info = shortcuts.get_object_or_404(Domain, pk=domain_id, owner=request.user)
    if request.method != 'POST':
        form = forms.DomainDetailsForm(current_user=request.user, instance=domain_info)
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    form = forms.DomainDetailsForm(current_user=request.user, data=request.POST, instance=domain_info)
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    if form.instance.epp_id:
        if not zmaster.domain_check_create_update_renew(
            domain_object=form.instance,
            sync_contacts=True,
            sync_nameservers=True,
            renew_years=None,
            save_to_db=False,
            raise_errors=False,
            log_events=True,
            log_transitions=True,
        ):
            messages.error(request, 'There were technical problems with domain info processing. '
                                    'Please try again later or contact customer support.')
            return shortcuts.render(request, 'front/account_domain_details.html', {
                'form': form,
            })
    form.save()
    messages.success(request, 'Domain details successfully updated.')
    # return shortcuts.redirect('account_domains')
    return shortcuts.render(request, 'front/account_domain_details.html', {
        'form': form,
    })


@login_required
def account_domain_transfer(request):
    domain = shortcuts.get_object_or_404(Domain, name=request.GET['domain_name'], owner=request.user)
    transfer_code = helpers.get_transfer_code()
    # TODO Send this code to the Cocca.
    return shortcuts.render(request, 'front/account_domain_transfer.html', {
        'transfer_code': transfer_code,
        'domain_name': domain.name,
    })


class AccountProfileView(UpdateView, BaseLoginRequiredMixin):
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


class AccountContactCreateView(CreateView, BaseLoginRequiredMixin):
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


class AccountContactUpdateView(UpdateView, BaseLoginRequiredMixin):
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


class AccountContactDeleteView(DeleteView, BaseLoginRequiredMixin):
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


class AccountContactsListView(ListView, BaseLoginRequiredMixin):
    template_name = 'front/account_contacts.html'
    model = Contact
    paginate_by = 10

    def get_queryset(self):
        return zcontacts.list_contacts(self.request.user)


@login_required
def domain_lookup(request):
    domain_name = request.GET.get('domain_name')
    if not domain_name:
        return shortcuts.render(request, 'front/domain_lookup.html', {
            'result': None,
        })

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

    return shortcuts.render(request, 'front/domain_lookup.html', {
        'result': result,
        'domain_name': domain_name,
    })
