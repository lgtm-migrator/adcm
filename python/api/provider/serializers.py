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
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import (
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    SerializerMethodField,
)

from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.utils import CommonAPIURL, ObjectURL, filter_actions
from cm.adcm_config import get_main_info
from cm.models import Action, HostProvider
from cm.upgrade import get_upgrade


class ProviderSerializer(HyperlinkedModelSerializer):
    url = HyperlinkedIdentityField(view_name="hostprovider-detail", lookup_url_kwarg="provider_pk")
    name = CharField()
    prototype_id = IntegerField()
    description = CharField(required=False)

    class Meta:
        model = HostProvider
        fields = (
            "id",
            "url",
            "name",
            "prototype_id",
            "description",
            "state",
            "before_upgrade",
        )
        extra_kwargs = {"state": {"read_only": True}, "before_upgrade": {"read_only": True}}


class ProviderDetailSerializer(ProviderSerializer):
    prototype = HyperlinkedIdentityField(view_name="provider-prototype-detail", lookup_url_kwarg="prototype_pk")
    config = CommonAPIURL(view_name="object-config")
    action = CommonAPIURL(view_name="object-action")
    upgrade = HyperlinkedIdentityField(view_name="hostprovider-upgrade-list", lookup_url_kwarg="provider_pk")
    host = ObjectURL(read_only=True, view_name="host")
    concerns = ConcernItemSerializer(many=True, read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name="group-config-list")

    class Meta:
        model = HostProvider
        fields = (
            *ProviderSerializer.Meta.fields,
            "edition",
            "license",
            "bundle_id",
            "prototype",
            "config",
            "action",
            "upgrade",
            "host",
            "multi_state",
            "concerns",
            "locked",
            "group_config",
        )


class ProviderUISerializer(ProviderSerializer):
    action = CommonAPIURL(view_name="object-action")
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgrade = HyperlinkedIdentityField(view_name="hostprovider-upgrade-list", lookup_url_kwarg="provider_pk")
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)

    class Meta:
        model = HostProvider
        fields = (
            *ProviderSerializer.Meta.fields,
            "edition",
            "locked",
            "action",
            "prototype_version",
            "prototype_name",
            "prototype_display_name",
            "upgrade",
            "upgradable",
            "concerns",
        )

    @staticmethod
    def get_upgradable(obj: HostProvider) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: HostProvider) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: HostProvider) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: HostProvider) -> str | None:
        return obj.prototype.display_name


class ProviderDetailUISerializer(ProviderDetailSerializer):
    actions = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    class Meta:
        model = HostProvider
        fields = (
            *ProviderDetailSerializer.Meta.fields,
            "actions",
            "prototype_version",
            "prototype_name",
            "prototype_display_name",
            "upgradable",
            "concerns",
            "main_info",
        )

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["provider_pk"] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    @staticmethod
    def get_upgradable(obj: HostProvider) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: HostProvider) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: HostProvider) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: HostProvider) -> str | None:
        return obj.prototype.display_name

    @staticmethod
    def get_main_info(obj: HostProvider) -> str | None:
        return get_main_info(obj)
