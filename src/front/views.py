
from django import shortcuts
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.http import HttpResponseRedirect

from back.models.domain import Domain
from back.models.contact import Contact

from back import domains
from back import contacts
from back import zones
from back import users
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


def account_domains(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if not request.user.profile.is_complete():
        messages.success(request, 'Please provide your contact information to be able to register new domains.')
        return account_profile(request)
    if len(contacts.list_contacts(request.user)) == 0:
        messages.success(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
        return account_contacts(request)
    domain_objects = domains.list_domains(request.user.email)
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


def account_domain_create(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if not request.user.profile.is_complete():
        messages.success(request, 'Please provide your contact information to be able to register new domains.')
        return account_profile(request)
    if len(contacts.list_contacts(request.user)) == 0:
        messages.success(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
        return account_contacts(request)
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
    form_to_save = form.save(commit=False)
    form_to_save.name = domain_name
    # form_to_save.expiry_date = datetime.now()
    # form_to_save.create_date = datetime.now()
    form_to_save.owner = request.user
    form_to_save.zone = zones.make(domain_tld)
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_domain_details.html', {
            'form': form,
        })
    form_to_save.save()
    return account_domains(request)


def account_domain_edit(request, domain_id):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if not request.user.profile.is_complete():
        messages.success(request, 'Please provide your contact information to be able to register new domains.')
        return account_profile(request)
    if len(contacts.list_contacts(request.user)) == 0:
        messages.success(request, 'Please create your first contact person and provide your contact information to be able to register new domains.')
        return account_contacts(request)
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
    form.save()
    return account_domains(request)


def account_profile(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if request.method == 'POST':
        form = forms.AccountProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            existing_contacts = contacts.list_contacts(request.user)
            if not existing_contacts:
                new_contact = contacts.create_from_profile(request.user, form.instance)
                if contacts.execute_contact_sync(new_contact):
                    messages.success(request, 'Your profile information was successfully updated! Now you can register new domains.')
                    form.save()
                else:
                    messages.error(request, 'There were technical problems with contact details processing. '
                                            'Please try again later or contact customer support.')
            else:
                messages.success(request, 'Your profile information was successfully updated!')
                form.save()
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = forms.AccountProfileForm(instance=request.user.profile)
    return shortcuts.render(request, 'front/account_profile.html', {
        'form': form,
    })


def account_contact_create(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    if request.method != 'POST':
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': forms.ContactPersonForm(),
        })
    form = forms.ContactPersonForm(request.POST)
    if not form.is_valid():
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': form,
        })
    form_to_save = form.save(commit=False)
    form_to_save.owner = request.user
    if not contacts.execute_contact_sync(form_to_save.instance):
        messages.error(request, 'There were technical problems with contact details processing. '
                                'Please try again later or contact customer support.')
        return shortcuts.render(request, 'front/account_contact_create.html', {
            'form': forms.ContactPersonForm(),
        })
    form_to_save.save()
    return account_contacts(request)


def account_contact_edit(request, contact_id):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
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
    if not contacts.execute_contact_sync(form.instance):
        messages.error(request, 'There were technical problems with contact details processing. '
                                'Please try again later or contact customer support.')
        return shortcuts.render(request, 'front/account_contact_edit.html', {
            'form': form,
        })
    form.save()
    messages.success(request, 'Contact details successfully updated.')
    return account_contacts(request)


def account_contacts(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    return shortcuts.render(request, 'front/account_contacts.html', {
        'objects': contacts.list_contacts(request.user),
    })


def domain_lookup(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('login')
    domain_name = request.GET.get('domain_name')
    check_result = zmaster.domains_check(domain_names=[domain_name, ],)
    if check_result is None:
        # If service is unavailable, return 'Unavailable'
        is_domain_available = 'Unavailable'
    else:
        if not check_result.get(domain_name):
            is_domain_available = True
        else:
            is_domain_available = False
    return shortcuts.render(request, 'front/domain_lookup.html', {
        'is_domain_available': is_domain_available,
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
