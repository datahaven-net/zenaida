from datetime import datetime

from django import shortcuts
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
# from django.conf import settings

from back.models import zone, domain
from back import domains
from back import contacts
from back import zones
from front import forms
from zepp import zmaster


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


def index_page(request):
    total_domains = 0
    if request.user.is_authenticated:
        total_domains = len(request.user.domains.all())
    return shortcuts.render(request, 'base/index.html', {
        'total_domains': total_domains,
    })


def account_domains(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
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
    domain_info = shortcuts.get_object_or_404(domain.Domain, pk=domain_id, owner=request.user)
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
            form.save()
            messages.success(request, 'Your profile information was successfully updated!')
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
    error = False
    if request.method == 'POST':
        form = forms.ContactPersonForm(request.POST)
        form_to_save = form.save(commit=False)
        form_to_save.owner = request.user
        if form.is_valid():
            form_to_save.save()
            # When creation of contact person is successful, return back to the page that user came from.
            next_page = request.POST.get('next_page', '/')
            return HttpResponseRedirect(next_page)
        else:
            error = True
    # While showing the form, get the url of the page that user came from.
    next_page = request.META.get('HTTP_REFERER')
    return shortcuts.render(request, 'front/account_contact_create.html', {
        'form': forms.ContactPersonForm(),
        'contact_person_error': error,
        'next_page': next_page,
    })


def account_contact_edit(request, contact_id):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    contact_person = shortcuts.get_object_or_404(domain.Contact.contacts, pk=contact_id, owner=request.user)
    if request.method == 'POST':
        form = forms.ContactPersonForm(request.POST, instance=contact_person)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/contacts/')
    else:
        form = forms.ContactPersonForm(instance=contact_person)
    return shortcuts.render(request, 'front/account_contact_edit.html', {
        'form': form,
    })


def account_contacts(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    return shortcuts.render(request, 'front/account_contacts.html', {
        'objects': contacts.list_contacts(request.user),
    })


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


# class ContactsView(TemplateView):
#     template_name = 'front/account_contacts.html'
# 
#     @method_decorator(login_required)
#     def dispatch(self, request, *args, **kwargs):
#         self.extra_context = {
#             'contacts': request.user.contacts.all(),
#         }
#         return super().dispatch(request, *args, **kwargs)
# 
#     def post(self, request, *args, **kwargs):
#         from automats import contact_synchronizer
#         contact_id = request.POST['contact_id']
#         contact_object = contacts.by_id(contact_id)
#         cs = contact_synchronizer.ContactSynchronizer()
#         cs.event('run', contact_object)
#         return JsonResponse({'contact_id': contact_id, })
