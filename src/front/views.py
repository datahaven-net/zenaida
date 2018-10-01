from django.shortcuts import render, redirect
from django.contrib import messages

from back.domains import list_domains
from front.forms import DomainLookupForm, AccountProfileForm
from zepp.zmaster import domain_check


def domain_lookup(request):
    if not request.user.is_authenticated:
        return redirect('index')
    result = ''
    if request.method != 'POST':
        form = DomainLookupForm()
    else:
        form = DomainLookupForm(request.POST)
        if form.is_valid():
            result = domain_check(domain=form.cleaned_data['domain_name'], return_string=True)
    return render(request, 'front/domain_lookup.html', {'form': form, 'result': result, }, )


def account_overview(request):
    if not request.user.is_authenticated:
        return redirect('index')
    return render(request, 'front/account_overview.html', {
        'domains': list_domains(request.user.email),
    }, )


def account_domains(request):
    if not request.user.is_authenticated:
        return redirect('index')
    return render(request, 'front/account_domains.html', {
        'domains': list_domains(request.user.email),
    }, )


def account_profile(request):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AccountProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile information was successfully updated!')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = AccountProfileForm(instance=request.user.profile)
    return render(request, 'front/account_profile.html', {'form': form, }, )
