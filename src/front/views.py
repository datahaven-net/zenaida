from django.shortcuts import render, redirect
from django.contrib import messages

from back import domains
from front import forms
from zepp import zmaster


def domain_create(request):
    if not request.user.is_authenticated:
        return redirect('index')
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
    if not request.user.is_authenticated:
        return redirect('index')
    result = ''
    if request.method != 'POST':
        form = forms.DomainLookupForm()
    else:
        form = forms.DomainLookupForm(request.POST)
        if form.is_valid():
            result = zmaster.domain_check(domain=form.cleaned_data['domain_name'], return_string=True)
    return render(request, 'front/domain_lookup.html', {
        'form': form,
        'result': result,
    }, )


def account_overview(request):
    if not request.user.is_authenticated:
        return redirect('index')
    return render(request, 'front/account_overview.html', {
        'domains': domains.list_domains(request.user.email),
    }, )


def account_domains(request):
    if not request.user.is_authenticated:
        return redirect('index')
    return render(request, 'front/account_domains.html', {
        'domains': domains.list_domains(request.user.email),
    }, )


def account_profile(request):
    if not request.user.is_authenticated:
        return redirect('index')
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
