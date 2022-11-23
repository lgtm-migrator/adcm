# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django_filters.rest_framework import ChoiceFilter, FilterSet, NumberFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated

from api.base_view import GenericUIViewSet
from api.concern.serializers import (
    ConcernItemDetailSerializer,
    ConcernItemSerializer,
    ConcernItemUISerializer,
)
from cm.errors import AdcmEx
from cm.models import ConcernCause, ConcernItem, ConcernType

OBJECT_TYPES = {
    "adcm": "adcm",
    "cluster": "cluster",
    "service": "clusterobject",
    "component": "servicecomponent",
    "provider": "hostprovider",
    "host": "host",
}
CHOICES = list(zip(OBJECT_TYPES, OBJECT_TYPES))


class ConcernFilter(FilterSet):
    type = ChoiceFilter(choices=ConcernType.choices)
    cause = ChoiceFilter(choices=ConcernCause.choices)
    object_id = NumberFilter(label="Related object ID")
    object_type = ChoiceFilter(label="Related object type", choices=CHOICES, method="filter_by_object")
    owner_type = ChoiceFilter(choices=CHOICES, method="filter_by_owner_type")

    class Meta:
        model = ConcernItem
        fields = [
            "name",
            "type",
            "cause",
            "object_type",
            "object_id",
            "owner_type",
            "owner_id",
        ]

    @staticmethod
    def filter_by_owner_type(queryset: QuerySet, value: str):
        owner_type = ContentType.objects.get(app_label="cm", model=OBJECT_TYPES[value])
        return queryset.filter(owner_type=owner_type)

    def filter_by_object(self, queryset: QuerySet, value: str):
        object_id = self.request.query_params.get("object_id")
        filters = {f"{OBJECT_TYPES[value]}_entities__id": object_id}
        return queryset.filter(**filters)

    def is_valid(self):
        object_type = self.request.query_params.get("object_type")
        object_id = self.request.query_params.get("object_id")
        both_present = all((object_id, object_type))
        none_present = not any((object_id, object_type))
        if not (both_present or none_present):
            raise AdcmEx(
                "BAD_QUERY_PARAMS",
                msg="Both object_type and object_id params are expected or none of them",
            )

        return super().is_valid()


class ConcernItemViewSet(ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = ConcernItem.objects.all()
    serializer_class = ConcernItemSerializer
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = "concern_pk"
    filterset_class = ConcernFilter
    ordering_fields = ("name",)

    def get_serializer_class(self):
        if self.is_for_ui():
            return ConcernItemUISerializer
        if self.action == "retrieve":
            return ConcernItemDetailSerializer
        return super().get_serializer_class()
