from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone

from questions.models import Answer, Question, Tag

POPULAR_TAGS_KEY = 'sidebar:popular-tags'
BEST_MEMBERS_KEY = 'sidebar:best-members'


def cached_sidebar(key, load):
    values = cache.get(key)
    if values is None:
        values = load()
        cache.set(key, values)
    return values


def popular_tags():
    since = timezone.now() - relativedelta(months=3)
    return list(Tag.objects.popular(since).values_list('name', flat=True))


def best_members():
    since = timezone.now() - timedelta(weeks=1)
    scores = {}
    for model in (Question, Answer):
        leaders = (
            model.objects.filter(created_at__gte=since)
            .values('author_id')
            .annotate(score=Max('rating'))
            .order_by('-score', 'author_id')[:10]
        )
        for row in leaders:
            author_id, score = row['author_id'], row['score']
            scores[author_id] = max(scores.get(author_id, score), score)

    user_ids = sorted(scores, key=lambda pk: (-scores[pk], pk))[:10]
    users = get_user_model().objects.in_bulk(user_ids)
    return [users[pk].first_name or users[pk].username for pk in user_ids if pk in users]
