import datetime

from django import shortcuts
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from back.models.domain import Domain
from back.models.contact import Contact

from back import domains
from back import contacts
from back import zones
from front import forms
from zepp import zmaster


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
        messages.info(request, 'Please provide your contact information to be able to register new domains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(contacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
        # return account_contacts(request)
        return shortcuts.redirect('account_contacts')
    domain_objects = domains.list_domains(request.user.email)
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
        messages.info(request, 'Please provide your contact information to be able to register new domains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(contacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
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
    if not zones.is_supported(domain_tld):
        messages.error(request, 'Domain zone ".%s" is not supported by that server.' % domain_tld)
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    domain_obj = form.save(commit=False)
    domains.create(
        domain_name=domain_name,
        owner=request.user,
        create_date=timezone.now(),
        expiry_date=timezone.now() + datetime.timedelta(days=365),
        registrant=contacts.get_registrant(request.user),
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
        messages.info(request, 'Please provide your contact information to be able to register new domains.')
        # return account_profile(request)
        return shortcuts.redirect('account_profile')
    if len(contacts.list_contacts(request.user)) == 0:
        messages.info(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
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
    # TODO Make a call to get a transfer code for domain_name
    transfer_code = '12345'
    return shortcuts.render(request, 'front/account_domain_transfer.html', {
        'transfer_code': transfer_code,
        'domain_name': domain.name,
    })


@login_required
def account_profile(request):
    if request.method != 'POST':
        return shortcuts.render(request, 'front/account_profile.html', {
            'form': forms.AccountProfileForm(instance=request.user.profile),
        })
    
    form = forms.AccountProfileForm(request.POST, instance=request.user.profile)
    if not form.is_valid():
        messages.error(request, 'Please correct the error below.')
        return shortcuts.render(request, 'front/account_profile.html', {
            'form': form,
        })
        
    existing_contacts = contacts.list_contacts(request.user)
    if not existing_contacts:
        new_contact = contacts.create_from_profile(request.user, form)
        if not zmaster.contact_create_update(new_contact):
            messages.error(request, 'There were technical problems with contact details processing. '
                                        'Please try again later or contact customer support.')
            return shortcuts.render(request, 'front/account_profile.html', {
                'form': form,
            })

    existing_registrant = contacts.get_registrant(request.user)
    if not existing_registrant:
        new_registrant = contacts.create_registrant_from_profile(request.user, form)
        if not zmaster.contact_create_update(new_registrant):
            messages.error(request, 'There were technical problems with contact details processing. '
                                        'Please try again later or contact customer support.')
            return shortcuts.render(request, 'front/account_profile.html', {
                'form': form,
            })
    else:
        contacts.update_registrant_from_profile(existing_registrant, form)
        if not zmaster.contact_create_update(existing_registrant):
            messages.error(request, 'There were technical problems with contact details processing. '
                                        'Please try again later or contact customer support.')
            return shortcuts.render(request, 'front/account_profile.html', {
                'form': form,
            })

    form.save()

    if existing_registrant and existing_contacts:
        messages.success(request, 'Your profile information was successfully updated.')
    else:
        messages.success(request, 'Your profile information was successfully updated, you can register new domains now.')
    return shortcuts.render(request, 'front/account_profile.html', {
        'form': form,
    })


@login_required
def account_contact_create(request):
    if request.method != 'POST':
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': forms.ContactPersonForm(),
        })
    form = forms.ContactPersonForm(request.POST)
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': form,
        })
    form = form.save(commit=False)
    form.owner = request.user
    if not zmaster.contact_create_update(form):
        messages.error(request, 'There were technical problems with contact details processing. '
                                'Please try again later or contact customer support.')
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': forms.ContactPersonForm(),
        })
    form.save()
    messages.success(request, 'New contact person successfully added.')
    return shortcuts.redirect('account_contacts')


@login_required
def account_contact_edit(request, contact_id):
    contact_person = shortcuts.get_object_or_404(Contact, pk=contact_id, owner=request.user)
    if request.method != 'POST':
        form = forms.ContactPersonForm(instance=contact_person)
        return shortcuts.render(request, 'front/account_contact_edit.html', {
            'form': form,
        })
    form = forms.ContactPersonForm(request.POST, instance=contact_person)
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_contact_edit.html', {
            'form': form,
        })
    if not zmaster.contact_create_update(form.instance):
        messages.error(request, 'There were technical problems with contact details processing. '
                                'Please try again later or contact customer support.')
        return shortcuts.render(request, 'front/account_contact_edit.html', {
            'form': form,
        })
    form.save()
    messages.success(request, 'Contact person details successfully updated.')
    return shortcuts.redirect('account_contacts')


@login_required
def account_contact_delete(request, contact_id):
    contact_person = shortcuts.get_object_or_404(Contact, pk=contact_id, owner=request.user)
    contact_person.delete()
    messages.success(request, 'Contact person successfully deleted.')
    return shortcuts.redirect('account_contacts')


@login_required
def account_contacts(request):
    return shortcuts.render(request, 'front/account_contacts.html', {
        'objects': contacts.list_contacts(request.user),
    })


@login_required
def domain_lookup(request):
    domain_name = request.GET.get('domain_name')
    if not domain_name:
        return shortcuts.render(request, 'front/domain_lookup.html', {
            'result': None,
        })
    check_result = zmaster.domains_check(domain_names=[domain_name, ],)
    if check_result is None:
        # If service is unavailable, return 'error'
        result = 'error'
    else:
        if check_result.get(domain_name):
            result = 'exist'
        else:
            result = 'not exist'
    return shortcuts.render(request, 'front/domain_lookup.html', {
        'result': result,
        'domain_name': domain_name,
    })


def contact_us(request):
    return shortcuts.render(request, 'front/contact_us.html')


def get_faq(request):
    return shortcuts.render(request, 'front/faq.html')


def get_faq_epp(request):
    return shortcuts.render(request, 'faq/faq_epp.html')


def get_faq_auctions(request):
    return shortcuts.render(request, 'faq/faq_auctions.html')


def get_faq_payments(request):
    return shortcuts.render(request, 'faq/faq_payments.html')


def get_correspondentbank(request):
    return shortcuts.render(request, 'faq/faq_correspondentbank.html')


def get_registrars(request):
    return shortcuts.render(request, 'faq/faq_registrars.html')
