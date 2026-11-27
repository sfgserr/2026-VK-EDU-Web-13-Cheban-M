from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from core.models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0


admin.site.unregister(User)


@admin.register(User)
class ForumUserAdmin(UserAdmin):
    inlines = [ProfileInline]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'avatar']
    search_fields = ['user__username', 'user__email']
    list_filter = ['user__is_active']
    list_select_related = ['user']
    raw_id_fields = ['user']
