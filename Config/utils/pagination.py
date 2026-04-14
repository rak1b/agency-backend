from django.conf import settings
from rest_framework import pagination
from rest_framework.response import Response

import logging
logger = logging.getLogger('django')

class PageNumberPagination(pagination.PageNumberPagination):
    # allow client to set page size via ?page_size=
    page_size_query_param = 'page_size'
    # set a reasonable default, if you like
    # page_size = 2

    def get_paginated_response(self, data):
        return Response({
            'total_items': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'active_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'results': data
        })