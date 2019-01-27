from django import shortcuts
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseRedirect
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings
from datetime import datetime

from back.models import zone, domain
from back import domains
from back import contacts
from front import forms
from zepp import zmaster


def domain_lookup(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    is_domain_registered = ''
    link = ''
    domain_name = ''
    if request.method != 'POST':
        form = forms.DomainLookupForm()
    else:
        form = forms.DomainLookupForm(request.POST)
        if form.is_valid():
            domain_name = form.cleaned_data['domain_name']
            check_result = zmaster.domains_check(
                [domain_name, ],
            )
            if check_result is None:
                # If service is unavailable, return 'Unavailable'
                is_domain_registered = 'Unavailable'
            else:
                if check_result.get(domain_name):
                    is_domain_registered = True
                else:
                    is_domain_registered = False
                    link = '/domains/add?domain_name=%s' % form.cleaned_data['domain_name']
    return shortcuts.render(request, 'front/domain_lookup.html', {
        'form': form,
        'link': link,
        'is_domain_registered': str(is_domain_registered),
        'domain_name': domain_name,
    })


def index_page(request):
    message = ''
    link = ''
    domain_name = ''
    if request.method != 'POST':
        form = forms.DomainLookupForm()
    else:
        form = forms.DomainLookupForm(request.POST)
        if form.is_valid():
            domain_name = form.cleaned_data['domain_name']
            check_result = zmaster.domains_check(domain_names=[domain_name, ], )
            if check_result is None:
                message = 'service temporary unavailable'
            else:
                if check_result.get(domain_name):
                    message = 'domain already registered'
                else:
                    message = 'domain is available'
                    link = '/domains/add?domain_name=%s' % form.cleaned_data['domain_name']
    response = {
        'form': form,
        'message': message,
        'link': link,
        'domains': [],
        'domain_name': domain_name,
    }
    if request.user.is_authenticated:
        response['domains'] += domains.list_domains(request.user.email)
    return shortcuts.render(request, 'front/index.html', response)


def account_domains(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    domain_objects = domains.list_domains(request.user.email)
    page = request.GET.get('page', 1)
    paginator = Paginator(domain_objects, 3)

    try:
        domain_objects = paginator.page(page)
    except PageNotAnInteger:
        domain_objects = paginator.page(1)
    except EmptyPage:
        domain_objects = paginator.page(paginator.num_pages)

    return shortcuts.render(request, 'front/account_domains.html', {
        'objects': domain_objects,
    }, )


def account_domain_add(request):
    if not request.user.is_authenticated:
        return shortcuts.redirect('index')
    resp = None
    contact_amount = len(request.user.contacts.all())
    if request.method != 'POST':
        form = forms.DomainAddForm(request.user)
    else:
        domain_name = request.GET['domain_name']
        form = forms.DomainAddForm(request.user, request.POST)
        form_to_save = form.save(commit=False)
        form_to_save.name = domain_name
        form_to_save.expiry_date = datetime.now()
        form_to_save.create_date = datetime.now()
        form_to_save.owner = request.user

        zones = zone.Zone.zones.all()
        for zone_record in zones:
            if zone_record.name == domain_name.split('.')[-1].lower():
                form_to_save.zone = zone_record
            else:
                # TODO return error message if zone is not supported.
                pass
        if form.is_valid():
            form_to_save.save()
            resp = shortcuts.render(request, 'front/account_domain_add.html', {'registered': True})

    if not resp:
        resp = shortcuts.render(request, 'front/account_domain_add.html', {
            'form': form,
            'contact_amount': contact_amount
        })
    return resp
    

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
    }, )


def create_new_contact(request):
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
    return shortcuts.render(
        request, 'front/account_contacts_new.html',
        {'form': forms.ContactPersonForm(), 'contact_person_error': error, 'next_page': next_page}
    )


def edit_contact(request, contact_id):
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
    return shortcuts.render(request, 'front/account_contacts_edit.html', {'form': form})


def get_faq(request):
    return shortcuts.render(request, 'front/faq.html')


def get_faq_epp(request):
    return shortcuts.render(request, 'faq/faq_epp.html')


def get_faq_auctions(request):
    return shortcuts.render(request, 'faq/faq_auctions.html')


def get_faq_payments(request):
    return shortcuts.render(request, 'faq/faq_payments.html')


def get_correspondentbank(request):
    return shortcuts.render(request, 'faq/correspondentbank.html')


def get_registrars(request):
    return shortcuts.render(request, 'faq/registrars.html')


class ContactsView(TemplateView):
    template_name = 'front/account_contacts.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.extra_context = {
            'contacts': request.user.contacts.all(),
        }
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from automats import contact_synchronizer
        contact_id = request.POST['contact_id']
        contact_object = contacts.by_id(contact_id)
        cs = contact_synchronizer.ContactSynchronizer()
        cs.event('run', contact_object)
        return JsonResponse({'contact_id': contact_id, })
