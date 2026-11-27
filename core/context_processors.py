from core.sidebar import BEST_MEMBERS_KEY, POPULAR_TAGS_KEY, best_members, cached_sidebar, popular_tags


def sidebar(request):
    return {
        'popular_tags': cached_sidebar(POPULAR_TAGS_KEY, popular_tags),
        'best_members': cached_sidebar(BEST_MEMBERS_KEY, best_members),
    }
