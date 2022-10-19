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

from rest_framework.serializers import (
    BooleanField,
    CharField,
    FileField,
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    IntegerField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer
from api.action.serializers import StackActionDetailSerializer
from api.config.serializers import ConfigSerializer
from api.serializers import UpgradeSerializer
from cm.models import Bundle, ClusterObject, Prototype


class UploadBundleSerializer(EmptySerializer):
    file = FileField(help_text="bundle file for upload")


class LoadBundleSerializer(EmptySerializer):
    bundle_file = CharField()


class BundleSerializer(HyperlinkedModelSerializer):
    license_url = HyperlinkedIdentityField(
        view_name="bundle-license", lookup_field="pk", lookup_url_kwarg="bundle_pk"
    )
    update = HyperlinkedIdentityField(
        view_name="bundle-update", lookup_field="pk", lookup_url_kwarg="bundle_pk"
    )

    class Meta:
        model = Bundle
        fields = (
            "id",
            "name",
            "version",
            "edition",
            "license",
            "license_path",
            "license_hash",
            "hash",
            "description",
            "date",
            "license_url",
            "update",
            "url",
        )
        read_only_fields = fields
        extra_kwargs = {"url": {"lookup_url_kwarg": "bundle_pk"}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        proto = Prototype.objects.filter(bundle=instance, name=instance.name)
        data["adcm_min_version"] = proto[0].adcm_min_version
        data["display_name"] = proto[0].display_name

        return data


class PrototypeSerializer(EmptySerializer):
    bundle_id = IntegerField(read_only=True)
    id = IntegerField(read_only=True)
    path = CharField(read_only=True)
    name = CharField(read_only=True)
    display_name = CharField(required=False)
    version = CharField(read_only=True)
    bundle_edition = SerializerMethodField()
    description = CharField(required=False)
    type = CharField(read_only=True)
    required = BooleanField(read_only=True)
    url = HyperlinkedIdentityField(
        view_name="prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )

    @staticmethod
    def get_bundle_edition(obj):
        return obj.bundle.edition


class PrototypeSerializerMixin:
    @staticmethod
    def get_constraint(obj):
        if obj.type == "component":
            return obj.constraint

        return []

    @staticmethod
    def get_service_name(obj):
        if obj.type == "component":
            return obj.parent.name

        return ""

    @staticmethod
    def get_service_display_name(obj):
        if obj.type == "component":
            return obj.parent.display_name

        return ""

    @staticmethod
    def get_service_id(obj):
        if obj.type == "component":
            return obj.parent.id

        return None


class PrototypeUISerializer(PrototypeSerializer, PrototypeSerializerMixin):
    parent_id = IntegerField(read_only=True)
    version_order = IntegerField(read_only=True)
    shared = BooleanField(read_only=True)
    constraint = SerializerMethodField(read_only=True)
    requires = JSONField(read_only=True)
    bound_to = JSONField(read_only=True)
    adcm_min_version = CharField(read_only=True)
    monitoring = CharField(read_only=True)
    config_group_customization = BooleanField(read_only=True)
    venv = CharField(read_only=True)
    allow_maintenance_mode = BooleanField(read_only=True)
    service_name = SerializerMethodField(read_only=True)
    service_display_name = SerializerMethodField(read_only=True)
    service_id = SerializerMethodField(read_only=True)


class PrototypeDetailSerializer(PrototypeSerializer, PrototypeSerializerMixin):
    constraint = SerializerMethodField()
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    service_name = SerializerMethodField(read_only=True)
    service_display_name = SerializerMethodField(read_only=True)
    service_id = SerializerMethodField(read_only=True)


class PrototypeShort(ModelSerializer):
    class Meta:
        model = Prototype
        fields = ("name",)


class ExportSerializer(EmptySerializer):
    name = CharField(read_only=True)


class ImportSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    min_version = CharField(read_only=True)
    max_version = CharField(read_only=True)
    min_strict = BooleanField(required=False)
    max_strict = BooleanField(required=False)
    default = JSONField(read_only=True)
    required = BooleanField(read_only=True)
    multibind = BooleanField(read_only=True)


class ComponentPrototypeSerializer(PrototypeSerializer):
    constraint = JSONField(required=False)
    requires = JSONField(required=False)
    bound_to = JSONField(required=False)
    monitoring = CharField(read_only=True)
    url = HyperlinkedIdentityField(
        view_name="component-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )


class ServicePrototypeSerializer(PrototypeSerializer):
    shared = BooleanField(read_only=True)
    monitoring = CharField(read_only=True)
    url = HyperlinkedIdentityField(
        view_name="service-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )


class ServiceDetailPrototypeSerializer(ServicePrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    components = ComponentPrototypeSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)


class BundleServiceUIPrototypeSerializer(ServicePrototypeSerializer):
    selected = SerializerMethodField()

    def get_selected(self, obj):
        cluster = self.context.get("cluster")
        try:
            ClusterObject.objects.get(cluster=cluster, prototype=obj)

            return True
        except ClusterObject.DoesNotExist:
            return False


class AdcmPrototypeSerializer(PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="adcm-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )


class ClusterPrototypeSerializer(PrototypeSerializer):
    license = SerializerMethodField()
    url = HyperlinkedIdentityField(
        view_name="cluster-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )

    @staticmethod
    def get_license(obj):
        return obj.bundle.license


class HostPrototypeSerializer(PrototypeSerializer):
    monitoring = CharField(read_only=True)
    url = HyperlinkedIdentityField(
        view_name="host-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )


class ProviderPrototypeSerializer(PrototypeSerializer):
    license = SerializerMethodField()
    url = HyperlinkedIdentityField(
        view_name="provider-prototype-detail", lookup_field="pk", lookup_url_kwarg="prototype_pk"
    )

    @staticmethod
    def get_license(obj):
        return obj.bundle.license


class ProviderPrototypeDetailSerializer(ProviderPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)


class HostPrototypeDetailSerializer(HostPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class ComponentPrototypeDetailSerializer(ComponentPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class AdcmPrototypeDetailSerializer(AdcmPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class ClusterPrototypeDetailSerializer(ClusterPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)
