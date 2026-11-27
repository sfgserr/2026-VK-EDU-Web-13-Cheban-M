POPULAR_TAGS = ['python', 'django', 'mysql', 'css', 'bootstrap', 'git', 'linux', 'javascript']
BEST_MEMBERS = ['Mr. Freeman', 'Dr. House', 'Bender', 'Queen Victoria', 'V. Pupkin']


def sidebar(request):
    return {
        'popular_tags': POPULAR_TAGS,
        'best_members': BEST_MEMBERS,
    }
