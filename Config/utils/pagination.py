from django.conf import settings
from rest_framework import pagination
from rest_framework.response import Response

import logging
logger = logging.getLogger('django')

class DefaultPageNumberPagination(pagination.PageNumberPagination):
    """
    Global pagination class that keeps DRF's default response shape while
    allowing clients to override page size with ``?page_size=``.
    """

    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_schema_operation_parameters(self, view):
        """
        Make sure Swagger/OpenAPI always exposes pagination query params.
        """
        return [
            {
                "name": self.page_query_param,
                "required": False,
                "in": "query",
                "description": "A page number within the paginated result set.",
                "schema": {"type": "integer"},
            },
            {
                "name": self.page_size_query_param,
                "required": False,
                "in": "query",
                "description": "Number of results to return per page.",
                "schema": {"type": "integer"},
            },
        ]


class PageNumberPagination(pagination.PageNumberPagination):
    # allow client to set page size via ?page_size=
    page_size_query_param = 'page_size'
    max_page_size = 200
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

    def get_schema_operation_parameters(self, view):
        """
        Keep docs in sync so custom paginated responses still show query params.
        """
        return [
            {
                "name": self.page_query_param,
                "required": False,
                "in": "query",
                "description": "A page number within the paginated result set.",
                "schema": {"type": "integer"},
            },
            {
                "name": self.page_size_query_param,
                "required": False,
                "in": "query",
                "description": "Number of results to return per page.",
                "schema": {"type": "integer"},
            },
        ]