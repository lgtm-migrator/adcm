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

from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.base_view import GenericUIView, GenericUIViewSet
from api.component.serializers import (
    ComponentChangeMaintenanceModeSerializer,
    ComponentDetailSerializer,
    ComponentDetailUISerializer,
    StatusSerializer,
)
from api.utils import (
    check_custom_perm,
    get_maintenance_mode_response,
    get_object_for_user,
)
from audit.utils import audit
from cm.api import update_mm_objects
from cm.models import Cluster, ClusterObject, HostComponent, ServiceComponent
from cm.status_api import make_ui_component_status
from rbac.viewsets import DjangoOnlyObjectPermissions


def get_component_queryset(queryset, user, kwargs):
    if "cluster_id" in kwargs:
        cluster = get_object_for_user(user, "cm.view_cluster", Cluster, id=kwargs["cluster_id"])
        co = get_object_for_user(user, "cm.view_clusterobject", ClusterObject, cluster=cluster, id=kwargs["service_id"])
        queryset = queryset.filter(cluster=cluster, service=co)
    elif "service_id" in kwargs:
        co = get_object_for_user(user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        queryset = queryset.filter(service=co)

    return queryset


# pylint: disable=too-many-ancestors
class ComponentViewSet(PermissionListMixin, ModelViewSet, GenericUIViewSet):
    queryset = ServiceComponent.objects.all()
    serializer_class = ComponentDetailSerializer
    lookup_url_kwarg = "component_id"
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ["cm.view_servicecomponent"]
    filterset_fields = ("cluster_id", "service_id")
    ordering_fields = ("state", "prototype__display_name", "prototype__version_order")

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        return get_component_queryset(queryset, self.request.user, self.kwargs)

    def get_serializer_class(self):
        if self.is_for_ui():
            return ComponentDetailUISerializer
        return super().get_serializer_class()


class ComponentMaintenanceModeView(GenericUIView):
    queryset = ServiceComponent.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    serializer_class = ComponentChangeMaintenanceModeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "component_id"

    @update_mm_objects
    @audit
    def post(self, request: Request, **kwargs) -> Response:
        component = get_object_for_user(
            request.user, "cm.view_servicecomponent", ServiceComponent, id=kwargs["component_id"]
        )
        # pylint: disable=protected-access
        check_custom_perm(request.user, "change_maintenance_mode", component._meta.model_name, component)
        serializer = self.get_serializer(instance=component, data=request.data)
        serializer.is_valid(raise_exception=True)

        return get_maintenance_mode_response(obj=component, serializer=serializer)


class StatusList(GenericUIView):
    queryset = HostComponent.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = StatusSerializer

    def get(self, request, *args, **kwargs):
        queryset = get_component_queryset(ServiceComponent.objects.all(), request.user, kwargs)
        component = get_object_for_user(request.user, "cm.view_servicecomponent", queryset, id=kwargs["component_id"])
        if self._is_for_ui():
            host_components = self.get_queryset().filter(component=component)

            return Response(make_ui_component_status(component, host_components))

        return Response(self.get_serializer(component).data)
