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
from django.db import IntegrityError
from guardian.mixins import PermissionListMixin
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from api.base_view import GenericUIViewSet
from api.provider.serializers import (
    ProviderDetailSerializer,
    ProviderDetailUISerializer,
    ProviderSerializer,
    ProviderUISerializer,
)
from api.serializers import ProviderUpgradeSerializer
from api.utils import (
    AdcmFilterBackend,
    AdcmOrderingFilter,
    check_custom_perm,
    check_obj,
    get_object_for_user,
)
from audit.utils import audit
from cm.api import add_host_provider, delete_host_provider
from cm.errors import raise_adcm_ex
from cm.issue import update_hierarchy_issues
from cm.models import HostProvider, Prototype, Upgrade
from cm.upgrade import do_upgrade, get_upgrade
from rbac.viewsets import DjangoOnlyObjectPermissions


class ProviderViewSet(  # pylint: disable=too-many-ancestors
    ListModelMixin, CreateModelMixin, RetrieveModelMixin, PermissionListMixin, GenericUIViewSet
):

    queryset = HostProvider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    lookup_url_kwarg = "provider_pk"
    filterset_fields = ("name", "prototype_id")
    ordering_fields = ("name", "state", "prototype__display_name", "prototype__version_order")
    permission_required = ["cm.view_hostprovider"]

    def get_serializer_class(self):
        if self.is_for_ui():
            if self.action == "retrieve":
                return ProviderDetailUISerializer
            elif self.action == "list":
                return ProviderUISerializer
        if self.action == "retrieve":
            return ProviderDetailSerializer
        return super().get_serializer_class()

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                proto = check_obj(
                    Prototype, {"id": data.get("prototype_id"), "type": "provider"}, "PROTOTYPE_NOT_FOUND"
                )
                add_host_provider(
                    proto,
                    data.get("name"),
                    data.get("description", ""),
                )
                return Response()
            except IntegrityError:
                raise_adcm_ex("PROVIDER_CONFLICT")
        return Response()

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Remove host provider
        """
        provider = self.get_object()
        delete_host_provider(provider)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderUpgradeViewSet(RetrieveModelMixin, ListModelMixin, GenericUIViewSet):
    queryset = Upgrade.objects.all()
    serializer_class = ProviderUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (AdcmFilterBackend, AdcmOrderingFilter)
    lookup_url_kwarg = "upgrade_pk"

    def get_ordering(self):
        order = AdcmOrderingFilter()
        return order.get_ordering(self.request, self.get_queryset(), self)

    def list(self, request, *args, **kwargs):
        """
        List all available upgrades for specified host provider
        """
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_pk"])
        check_custom_perm(request.user, "view_upgrade_of", "hostprovider", provider)
        update_hierarchy_issues(provider)
        obj = get_upgrade(provider, self.get_ordering())
        serializer = self.serializer_class(obj, many=True, context={"provider_pk": provider.pk, "request": request})
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Show specified upgrade object available for specified host provider
        """
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_pk"])
        check_custom_perm(request.user, "view_upgrade_of", "hostprovider", provider)
        obj = check_obj(Upgrade, {"id": kwargs["upgrade_pk"], "bundle__name": provider.prototype.bundle.name})
        serializer = self.serializer_class(obj, context={"provider_pk": provider.pk, "request": request})
        return Response(serializer.data)

    @audit
    @action(methods=["post"], detail=True)
    def do(self, request, *args, **kwargs):
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_pk"])
        check_custom_perm(request.user, "do_upgrade_of", "hostprovider", provider)
        data = request.data
        upgrade = check_obj(Upgrade, kwargs["upgrade_pk"], "UPGRADE_NOT_FOUND")
        config = data.get("config", {})
        attr = data.get("attr", {})
        return Response(do_upgrade(provider, upgrade, config, attr, []))
