from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import transaction

from core.models import Profile


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label='Логин', max_length=150)
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Неверный логин или пароль.',
    }


class SignupForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(label='Email', max_length=254)
    first_name = forms.CharField(label='Имя', max_length=150)

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email', 'first_name')
        labels = {'username': 'Логин'}

    @transaction.atomic
    def save(self):
        user = super().save()
        Profile.objects.create(user=user)
        return user


class AvatarField(forms.ImageField):
    def to_python(self, data):
        if data is not None and data.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Размер аватара не должен превышать 2 МБ.')
        image = super().to_python(data)
        if image and image.image.format not in {'JPEG', 'PNG'}:
            raise forms.ValidationError('Загрузите изображение в формате JPG или PNG.')
        return image


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    email = forms.EmailField(label='Email', max_length=254)
    first_name = forms.CharField(label='Никнейм', max_length=150)
    avatar = AvatarField(
        label='Аватар', required=False, help_text='JPG или PNG, не более 2 МБ.',
        widget=forms.FileInput(attrs={'accept': '.jpg,.jpeg,.png'}),
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
    )

    class Meta:
        model = User
        fields = ('email', 'first_name')

    @transaction.atomic
    def save(self):
        user = self.instance
        user.save(update_fields=self.Meta.fields)
        profile, _ = Profile.objects.get_or_create(user=user)
        if self.cleaned_data['avatar']:
            profile.avatar = self.cleaned_data['avatar']
            profile.save(update_fields=['avatar'])
        return user
