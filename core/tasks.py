from celery import shared_task
from django.core.cache import cache

from core.sidebar import BEST_MEMBERS_KEY, POPULAR_TAGS_KEY, best_members, popular_tags


@shared_task
def refresh_popular_tags():
    cache.set(POPULAR_TAGS_KEY, popular_tags())


@shared_task
def refresh_best_members():
    cache.set(BEST_MEMBERS_KEY, best_members())
