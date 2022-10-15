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

from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)

from adcm.permissions import DjangoObjectPermissionsAudit
from api.action.serializers import StackActionSerializer
from api.base_view import (
    DetailView,
    GenericUIView,
    GenericUIViewSet,
    ModelPermOrReadOnlyForAuth,
    PaginatedView,
)
from api.stack.filters import PrototypeListFilter
from api.stack.serializers import (
    AdcmTypeDetailSerializer,
    AdcmTypeSerializer,
    BundleSerializer,
    ClusterTypeDetailSerializer,
    ClusterTypeSerializer,
    ComponentTypeDetailSerializer,
    ComponentTypeSerializer,
    HostTypeDetailSerializer,
    HostTypeSerializer,
    LicenseSerializer,
    LoadBundleSerializer,
    PrototypeDetailSerializer,
    PrototypeSerializer,
    PrototypeUISerializer,
    ProviderTypeDetailSerializer,
    ProviderTypeSerializer,
    ServiceDetailSerializer,
    ServiceSerializer,
    UploadBundleSerializer,
)
from api.utils import check_obj
from audit.utils import audit
from cm.api import accept_license, get_license, load_host_map, load_service_map
from cm.bundle import delete_bundle, load_bundle, update_bundle
from cm.models import (
    Action,
    Bundle,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    Upgrade,
)


class CsrfOffSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class UploadBundle(GenericUIView):
    queryset = Bundle.objects.all()
    serializer_class = UploadBundleSerializer
    authentication_classes = (CsrfOffSessionAuthentication, TokenAuthentication)
    parser_classes = (MultiPartParser,)

    @audit
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            return Response(status=HTTP_201_CREATED)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class LoadBundle(CreateModelMixin, GenericUIViewSet):
    queryset = Prototype.objects.all()
    serializer_class = LoadBundleSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)

    @action(methods=["put"], detail=False)
    def servicemap(self, request):
        load_service_map()

        return Response(status=HTTP_200_OK)

    @action(methods=["put"], detail=False)
    def hostmap(self, request):
        load_host_map()

        return Response(status=HTTP_200_OK)

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            bundle = load_bundle(serializer.validated_data.get("bundle_file"))
            srl = BundleSerializer(bundle, context={"request": request})

            return Response(srl.data)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class BundleList(PaginatedView):
    queryset = Bundle.objects.exclude(hash="adcm")
    serializer_class = BundleSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ("name", "version")
    ordering_fields = ("name", "version_order")


class BundleDetail(DetailView):
    queryset = Bundle.objects.all()
    serializer_class = BundleSerializer
    permission_classes = (ModelPermOrReadOnlyForAuth,)
    lookup_field = "id"
    lookup_url_kwarg = "bundle_id"
    error_code = "BUNDLE_NOT_FOUND"

    @audit
    def delete(self, request, *args, **kwargs):
        bundle = self.get_object()
        delete_bundle(bundle)

        return Response(status=HTTP_204_NO_CONTENT)


class BundleUpdate(GenericUIView):
    queryset = Bundle.objects.all()
    serializer_class = BundleSerializer

    @audit
    def put(self, request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, "BUNDLE_NOT_FOUND")
        update_bundle(bundle)
        serializer = self.get_serializer(bundle)

        return Response(serializer.data)


class BundleLicense(GenericUIView):
    action = "retrieve"
    queryset = Bundle.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get(request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, "BUNDLE_NOT_FOUND")
        body = get_license(bundle)
        url = reverse("accept-license", kwargs={"bundle_id": bundle.id}, request=request)

        return Response({"license": bundle.license, "accept": url, "text": body})


class AcceptLicense(GenericUIView):
    queryset = Bundle.objects.all()
    serializer_class = LicenseSerializer

    @audit
    def put(self, request, bundle_id):
        bundle = check_obj(Bundle, bundle_id, "BUNDLE_NOT_FOUND")
        accept_license(bundle)

        return Response(status=HTTP_200_OK)


class PrototypeList(PaginatedView):
    queryset = Prototype.objects.all()
    serializer_class = PrototypeSerializer
    serializer_class_ui = PrototypeUISerializer
    filterset_class = PrototypeListFilter
    ordering_fields = ("display_name", "version_order")


class ServiceList(PaginatedView):
    queryset = Prototype.objects.filter(type="service")
    serializer_class = ServiceSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")


class ServiceDetail(DetailView):
    queryset = Prototype.objects.filter(type="service")
    serializer_class = ServiceDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "prototype_id"
    error_code = "SERVICE_NOT_FOUND"

    def get_object(self):
        service = super().get_object()
        service.actions = Action.objects.filter(prototype__type="service", prototype__id=service.id)
        service.components = Prototype.objects.filter(parent=service, type="component")
        service.config = PrototypeConfig.objects.filter(prototype=service, action=None).order_by(
            "id"
        )
        service.exports = PrototypeExport.objects.filter(prototype=service)
        service.imports = PrototypeImport.objects.filter(prototype=service)

        return service


class ProtoActionDetail(GenericUIView):
    queryset = Action.objects.all()
    serializer_class = StackActionSerializer

    def get(self, request, action_id):
        obj = check_obj(Action, action_id, "ACTION_NOT_FOUND")
        serializer = self.get_serializer(obj)

        return Response(serializer.data)


class ServiceProtoActionList(GenericUIView):
    queryset = Action.objects.filter(prototype__type="service")
    serializer_class = StackActionSerializer

    def get(self, request, prototype_id):
        obj = self.get_queryset().filter(prototype_id=prototype_id)
        serializer = self.get_serializer(obj, many=True)

        return Response(serializer.data)


class ComponentList(PaginatedView):
    queryset = Prototype.objects.filter(type="component")
    serializer_class = ComponentTypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")


class HostTypeList(PaginatedView):
    queryset = Prototype.objects.filter(type="host")
    serializer_class = HostTypeSerializer
    filterset_fields = ("name", "bundle_id")
    ordering_fields = ("display_name", "version_order")


class ProviderTypeList(PaginatedView):
    queryset = Prototype.objects.filter(type="provider")
    serializer_class = ProviderTypeSerializer
    filterset_fields = ("name", "bundle_id", "display_name")
    ordering_fields = ("display_name", "version_order")
    permission_classes = (IsAuthenticated,)


class ClusterTypeList(PaginatedView):
    queryset = Prototype.objects.filter(type="cluster")
    serializer_class = ClusterTypeSerializer
    filterset_fields = ("name", "bundle_id", "display_name")
    ordering_fields = ("display_name", "version_order")


class AdcmTypeList(GenericUIView):
    queryset = Prototype.objects.filter(type="adcm")
    serializer_class = AdcmTypeSerializer
    filterset_fields = ("bundle_id",)

    def get(self, request, *args, **kwargs):
        obj = self.get_queryset()
        serializer = self.get_serializer(obj, many=True)

        return Response(serializer.data)


class AbstractPrototypeDetail(DetailView):
    lookup_field = "id"
    lookup_url_kwarg = "prototype_id"
    error_code = "PROTOTYPE_NOT_FOUND"

    def get_object(self):
        obj_type = super().get_object()
        act_set = []
        for adcm_action in Action.objects.filter(prototype__id=obj_type.id):
            adcm_action.config = PrototypeConfig.objects.filter(
                prototype__id=obj_type.id,
                action=adcm_action,
            )
            act_set.append(adcm_action)

        obj_type.actions = act_set
        obj_type.config = PrototypeConfig.objects.filter(prototype=obj_type, action=None)
        obj_type.imports = PrototypeImport.objects.filter(prototype=obj_type)
        obj_type.exports = PrototypeExport.objects.filter(prototype=obj_type)
        obj_type.upgrade = Upgrade.objects.filter(bundle=obj_type.bundle)

        return obj_type


class PrototypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.all()
    serializer_class = PrototypeDetailSerializer


class AdcmTypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.filter(type="adcm")
    serializer_class = AdcmTypeDetailSerializer


class ClusterTypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.filter(type="cluster")
    serializer_class = ClusterTypeDetailSerializer


class ComponentTypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.filter(type="component")
    serializer_class = ComponentTypeDetailSerializer


class HostTypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.filter(type="host")
    serializer_class = HostTypeDetailSerializer


class ProviderTypeDetail(AbstractPrototypeDetail):
    queryset = Prototype.objects.filter(type="provider")
    serializer_class = ProviderTypeDetailSerializer
