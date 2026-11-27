from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.forms import LoginForm, ProfileForm, SignupForm


class ForumLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = LoginForm


def signup(request):
    form = SignupForm(request.POST if request.method == 'POST' else None)
    if form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect('index')
    return render(request, 'core/signup.html', {'form': form})


@login_required
def profile(request):
    data = request.POST if request.method == 'POST' else None
    form = ProfileForm(data, request.FILES, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('profile')
    return render(request, 'core/profile.html', {'form': form})


@require_POST
def logout(request):
    next_url = request.POST.get('next')
    auth_logout(request)
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        return redirect(next_url)
    return redirect('index')
