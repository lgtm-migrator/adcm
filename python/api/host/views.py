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

from django_filters import rest_framework as drf_filters
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.api_views import (
    create,
    check_obj,
    PageView,
    DetailViewDelete,
    InterfaceView,
    GenericAPIPermStatusView,
)
from cm.api import remove_host_from_cluster, delete_host
from cm.errors import AdcmEx
from cm.models import (
    Cluster,
    HostProvider,
    Host,
    GroupConfig,
    ClusterObject,
    ServiceComponent,
    HostComponent,
)
from . import serializers
import cm.status_api


def has_host_perm(user, action_type, obj):
    if user.has_perm(f'cm.{action_type}_host_cluster', obj):
        return True
    return False


def check_host_perm(self, action_type, obj):
    if not has_host_perm(self.request.user, action_type, obj):
        self.permission_denied(
            self.request,
            message='You do not have permission to perform this action',
            code=status.HTTP_403_FORBIDDEN,
        )


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class HostFilter(drf_filters.FilterSet):
    cluster_is_null = drf_filters.BooleanFilter(field_name='cluster_id', lookup_expr='isnull')
    provider_is_null = drf_filters.BooleanFilter(field_name='provider_id', lookup_expr='isnull')
    group_config = drf_filters.ModelChoiceFilter(
        queryset=GroupConfig.objects.all(), field_name='group_config', label='GroupConfig'
    )
    hostcomponent__service_id = drf_filters.ModelChoiceFilter(
        queryset=ClusterObject.objects.all(),
        field_name='hostcomponent__service_id',
        label='HostComponentService',
        distinct=True,
    )
    hostcomponent__component_id = drf_filters.ModelChoiceFilter(
        queryset=ServiceComponent.objects.all(),
        field_name='hostcomponent__component_id',
        label='HostComponentComponent',
        distinct=True,
    )

    exclude_group_config__in = NumberInFilter(
        field_name='group_config', lookup_expr='in', label='ExcludeGroupConfigIn', exclude=True
    )

    class Meta:
        model = Host
        fields = [
            'cluster_id',
            'prototype_id',
            'provider_id',
            'fqdn',
            'cluster_is_null',
            'provider_is_null',
            'group_config',
            'hostcomponent__service_id',
            'hostcomponent__component_id',
            'exclude_group_config__in',
        ]


class HostList(PageView):
    """
    get:
    List all hosts

    post:
    Create new host
    """

    queryset = Host.objects.all()
    serializer_class = serializers.HostSerializer
    serializer_class_ui = serializers.HostUISerializer
    filterset_class = HostFilter
    filterset_fields = (
        'cluster_id',
        'prototype_id',
        'provider_id',
        'fqdn',
        'cluster_is_null',
        'provider_is_null',
        'group_config',
        'hostcomponent__service_id',
        'hostcomponent__component_id',
        'exclude_group_config__in',
    )  # just for documentation
    ordering_fields = (
        'fqdn',
        'state',
        'provider__name',
        'cluster__name',
        'prototype__display_name',
        'prototype__version_order',
    )

    def get(self, request, *args, **kwargs):
        """
        List all hosts
        """
        queryset = self.get_queryset()
        if 'cluster_id' in kwargs:  # List cluster hosts
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            queryset = self.get_queryset().filter(cluster=cluster)
        if 'provider_id' in kwargs:  # List provider hosts
            provider = check_obj(HostProvider, kwargs['provider_id'])
            queryset = self.get_queryset().filter(provider=provider)
        return self.get_page(self.filter_queryset(queryset), request)

    def post(self, request, *args, **kwargs):
        """
        Create host
        """
        serializer = self.serializer_class(
            data=request.data,
            context={
                'request': request,
                'cluster_id': kwargs.get('cluster_id', None),
                'provider_id': kwargs.get('provider_id', None),
            },
        )
        return create(serializer)


class HostListProvider(HostList):
    serializer_class = serializers.ProvideHostSerializer


class HostListCluster(HostList):
    serializer_class = serializers.ClusterHostSerializer
    permission_classes = (IsAuthenticated,)
    check_host_perm = check_host_perm

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            validated_data = serializer.validated_data
            if 'cluster_id' in kwargs:
                cluster = check_obj(Cluster, kwargs['cluster_id'])
            host = check_obj(Host, validated_data.get('id'))
            self.check_host_perm('unmap', cluster)
            cm.api.add_host_to_cluster(cluster, host)
            return Response(self.get_serializer(host).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def check_host(host, cluster):
    if host.cluster != cluster:
        msg = f"Host #{host.id} doesn't belong to cluster #{cluster.id}"
        raise AdcmEx('FOREIGN_HOST', msg)


class HostDetail(DetailViewDelete):
    """
    get:
    Show host
    """

    queryset = Host.objects.all()
    serializer_class = serializers.HostDetailSerializer
    serializer_class_ui = serializers.HostUISerializer
    permission_classes = (IsAuthenticated,)
    check_host_perm = check_host_perm
    lookup_field = 'id'
    lookup_url_kwarg = 'host_id'
    error_code = 'HOST_NOT_FOUND'

    def get(self, request, host_id, **kwargs):  # pylint: disable=arguments-differ)
        host = check_obj(Host, host_id)
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
        serial_class = self.select_serializer(request)
        serializer = serial_class(host, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, host_id, **kwargs):  # pylint: disable=arguments-differ
        """
        Delete host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        if 'cluster_id' in kwargs:
            # Remove host from cluster
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
            self.check_host_perm('unmap', cluster)
            remove_host_from_cluster(host)
        else:
            # Delete host (and all corresponding host services:components)
            delete_host(host)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatusList(GenericAPIPermStatusView, InterfaceView):
    serializer_class = serializers.StatusSerializer
    model_name = Host
    queryset = HostComponent.objects.all()

    def ui_status(self, host, host_components):
        host_map = cm.status_api.get_object_map(host, 'host')

        comp_list = []
        for hc in host_components:
            comp_list.append(
                {
                    'id': hc.component.id,
                    'name': hc.component.display_name,
                    'status': cm.status_api.get_component_status(hc.component),
                }
            )
        return {
            'id': host.id,
            'name': host.fqdn,
            'status': 32 if host_map is None else host_map.get('status', 0),
            'hc': comp_list,
        }

    def get(self, request, host_id, cluster_id=None):
        """
        Show all components in a specified host
        """
        host = check_obj(Host, host_id)
        hc_queryset = self.get_queryset().filter(host=host)
        if self.for_ui(request):
            return Response(self.ui_status(host, hc_queryset))
        else:
            serializer = self.serializer_class(host, context={'request': request})
            return Response(serializer.data)
