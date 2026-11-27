from core.models import Profile
from questions.models import Tag


def sidebar(request):
    return {
        'popular_tags': Tag.objects.popular(),
        'best_members': Profile.objects.best(),
    }
