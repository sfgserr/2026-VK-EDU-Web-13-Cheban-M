from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def paginate(objects_list, request, per_page=10):
    paginator = Paginator(objects_list, per_page)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    page.pagination_range = paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1)
    query = request.GET.copy()
    query.pop('page', None)
    page.query_string = query.urlencode()
    return page
