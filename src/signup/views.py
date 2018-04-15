from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect

from signup.forms import SignUpForm

@csrf_protect
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'registration/registration_form.html',
                  {'form': form},
#                   RequestContext(request),
                  )
