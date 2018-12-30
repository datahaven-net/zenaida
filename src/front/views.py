from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings

from back import domains
from back import contacts
from front import forms
from zepp import zmaster


def is_user_authenticated(authentication_status):
    if not authentication_status:
        return redirect('index')


def domain_create(request):
    is_user_authenticated(request.user.is_authenticated)
    if request.method != 'POST':
        form = forms.DomainCreateForm()
    else:
        form = forms.DomainCreateForm(request.POST)
        if form.is_valid():
            try:
                is_exist = zmaster.domain_check(
                    domain=form.cleaned_data['domain_name'],
                    raise_errors=True,
                    return_string=False,
                )
            except:
                messages.error(request, 'Failed to check domain status, please try again later.')
            else:
                if is_exist:
                    messages.error(request, 'Domain <b>%s</b> already registered.' % form.domain_name)
                else:
                    # TODO: domain to be created
#                     domains.create(
#                         name=form.domain_name,
#                         owner=request.user,
#                     )
                    messages.error(request, 'New domain <b>%s</b> was created, you have one day to register it' % form.domain_name)
    return render(request, 'front/domain_create.html', {
        'form': form,
    }, )


def domain_lookup(request):
    is_user_authenticated(request.user.is_authenticated)
    result = ''
    link = ''
    if request.method != 'POST':
        form = forms.DomainLookupForm()
    else:
        form = forms.DomainLookupForm(request.POST)
        if form.is_valid():
            result = zmaster.domain_check(
                domain_name=form.cleaned_data['domain_name'],
                # return_string=True,
            )
            if not result:
                link = '/domains/add?domain_name=%s' % form.cleaned_data['domain_name']
    return render(request, 'front/domain_lookup.html', {
        'form': form,
        'link': link,
        'result': str(result),
    }, )


def account_overview(request):
    result = ''
    if request.method != 'POST':
        form = forms.DomainLookupForm()
    else:
        form = forms.DomainLookupForm(request.POST)
        if form.is_valid():
            result = zmaster.domain_check(
                domain_name=form.cleaned_data['domain_name'],
                return_string=True,
            )
    resp = render(request, 'front/account_overview.html', {'form': form, 'result': result})
    if request.user.is_authenticated:
        response = {
            'domains': domains.list_domains(request.user.email),
        }
        resp = render(request, 'front/account_overview.html', {'form': form, 'result': result, 'response': response})
    return resp


def account_domains(request):
    is_user_authenticated(request.user.is_authenticated)
    return render(request, 'front/account_domains.html', {
        'domains': domains.list_domains(request.user.email),
    }, )


def account_domain_add(request):
    is_user_authenticated(request.user.is_authenticated)

    form = forms.DomainAddForm(request.user)
    resp = render(request, 'front/account_domain_add.html', {
        'form': form,
    })
    return resp
    

def account_profile(request):
    is_user_authenticated(request.user.is_authenticated)
    if request.method == 'POST':
        form = forms.AccountProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile information was successfully updated!')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = forms.AccountProfileForm(instance=request.user.profile)
    return render(request, 'front/account_profile.html', {
        'form': form,
    }, )


def get_faq(request):
    return render(request, 'front/faq.html')


def get_faq_epp(request):
    return render(request, 'faq/faq_epp.html')


def get_faq_auctions(request):
    return render(request, 'faq/faq_auctions.html')


def get_faq_payments(request):
    return render(request, 'faq/faq_payments.html')


def get_correspondentbank(request):
    return render(request, 'faq/correspondentbank.html')


def get_registrars(request):
    return render(request, 'faq/registrars.html')


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
