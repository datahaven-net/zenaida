from django.shortcuts import render, redirect

from front.forms import DomainLookupForm


def domain_check(domain):
    from zepp import client
    check = client.cmd_domain_check([domain, ], )
    if check['epp']['response']['result']['@code'] != '1000':
        raise client.EPPCommandFailed('EPP domain_check failed with error code: %s' % (
            check['epp']['response']['result']['@code'], ))
    if check['epp']['response']['resData']['chkData']['cd']['name']['@avail'] == '1':
        return False
    if not check['epp']['response']['resData']['chkData']['cd']['reason'].startswith('(00)'):
        raise client.EPPCommandFailed('EPP domain_check failed with reason: %s' % (
            check['epp']['response']['resData']['chkData']['cd']['reason']))
    return True


def domain_lookup(request):
    if not request.user.is_authenticated:
        return redirect('index')
    result = ''
    if request.method != 'POST':
        form = DomainLookupForm()
    else:
        form = DomainLookupForm(request.POST)
        if form.is_valid():
            try:
                result = 'exist' if domain_check(form.cleaned_data['domain_name']) else 'not exist'
            except Exception as exc:
                result = 'ERROR: ' + str(exc)
    return render(request, 'front/domain_lookup.html', {'form': form, 'result': result, }, )
