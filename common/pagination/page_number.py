            from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                success=True,
                data=data,
                meta={
                    "pagination": {
                        "page": self.page.number,
                        "page_size": self.get_page_size(self.request),
                        "pages": self.page.paginator.num_pages,
                        "count": self.page.paginator.count,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    }
                },
                error=None,
            )
        )
