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

from datetime import datetime

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import Bundle, Cluster, HostProvider, Prototype
from rbac.models import Policy, Role, RoleTypes, User


class TestPolicy(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        self.name = "test_policy"
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster_name = "test_cluster"
        self.cluster = Cluster.objects.create(name=self.cluster_name, prototype=prototype)
        self.role = Role.objects.create(
            name="test_role",
            display_name="test_role",
            type=RoleTypes.role,
            parametrized_by_type=["cluster", "provider"],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )
        self.policy = Policy.objects.create(name="test_policy_2", built_in=False)
        self.list_name = "rbac:policy-list"
        self.detail_name = "rbac:policy-detail"
        self.policy_updated_str = "Policy updated"
        self.provider = HostProvider.objects.create(
            name="test_provider",
            prototype=Prototype.objects.create(bundle=bundle, type="provider"),
        )

    def check_log(
        self,
        log: AuditLog,
        obj: Policy | None,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ) -> None:
        if obj:
            self.assertEqual(log.audit_object.object_id, obj.pk)
            self.assertEqual(log.audit_object.object_name, obj.name)
            self.assertEqual(log.audit_object.object_type, AuditObjectType.Policy)
            self.assertFalse(log.audit_object.is_deleted)
        else:
            self.assertFalse(log.audit_object)

        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, object_changes)

    def check_log_update(
        self,
        log: AuditLog,
        obj: Policy,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ) -> None:
        if object_changes is None:
            object_changes = {}

        return self.check_log(
            log=log,
            obj=obj,
            operation_name=self.policy_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=operation_result,
            user=user,
            object_changes=object_changes,
        )

    def test_create(self):
        response: Response = self.client.post(
            path=reverse(self.list_name),
            data={
                "name": self.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        policy = Policy.objects.get(pk=response.data["id"])

        self.check_log(
            log=log,
            obj=policy,
            operation_name="Policy created",
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(self.list_name),
                data={
                    "name": self.name,
                    "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=None,
            operation_name="Policy created",
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_delete(self):
        self.client.delete(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.policy,
            operation_name="Policy deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.policy,
            operation_name="Policy deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        new_test_description = "new_test_description"
        prev_description = self.policy.description
        self.client.put(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            data={
                "name": self.policy.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.policy.refresh_from_db()
        self.check_log_update(
            log=log,
            obj=self.policy,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
            object_changes={
                "current": {
                    "description": new_test_description,
                    "role": self.role.display_name,
                    "object": [
                        {
                            "id": self.cluster.pk,
                            "name": self.cluster_name,
                            "type": "cluster",
                        }
                    ],
                    "user": [self.test_user.username],
                },
                "previous": {
                    "description": prev_description,
                    "role": "",
                    "object": [],
                    "user": [],
                },
            },
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                data={
                    "name": self.policy.name,
                    "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                    "description": "new_test_description",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_update(
            log=log,
            obj=self.policy,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        new_test_description = "new_test_description"
        prev_description = self.policy.description
        self.client.patch(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            data={
                "object": [
                    {"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"},
                    {"id": self.provider.pk, "name": self.provider.name, "type": "provider"},
                ],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.policy.refresh_from_db()
        self.check_log_update(
            log=log,
            obj=self.policy,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
            object_changes={
                "current": {
                    "description": new_test_description,
                    "role": self.role.display_name,
                    "object": [
                        {
                            "id": self.cluster.pk,
                            "name": self.cluster_name,
                            "type": "cluster",
                        },
                        {
                            "id": self.provider.pk,
                            "name": self.provider.name,
                            "type": "provider",
                        },
                    ],
                    "user": [self.test_user.username],
                },
                "previous": {
                    "description": prev_description,
                    "role": "",
                    "object": [],
                    "user": [],
                },
            },
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                data={
                    "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                    "description": "new_test_description",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_update(
            log=log,
            obj=self.policy,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_patch_failed(self):
        try:
            self.client.patch(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                data={
                    "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                    "role": {},
                    "user": [{"id": self.test_user.pk}],
                    "description": "new_test_description",
                },
                content_type=APPLICATION_JSON,
            )
        except KeyError:
            pass

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_update(
            log=log,
            obj=self.policy,
            operation_result=AuditLogOperationResult.Fail,
            user=self.test_user,
        )
