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
from dataclasses import dataclass

from django.db.models import Model
from django.views import View
from rest_framework.response import Response

from audit.cases.common import get_audit_object_from_resp, get_or_create_audit_obj
from audit.models import (
    AUDIT_OBJECT_TYPE_TO_MODEL_MAP,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)


@dataclass
class RbacCaseData:
    view: View
    deleted_obj: Model
    obj_pk: int


def _rbac_case(
    obj_type: AuditObjectType,
    response: Response | None,
    data: RbacCaseData | None = None,
) -> tuple[AuditOperation, AuditObject | None]:
    if data:
        if data.view.action == "destroy":
            operation_type = AuditLogOperationType.Delete
            obj = data.deleted_obj
        else:
            operation_type = AuditLogOperationType.Update
            obj = AUDIT_OBJECT_TYPE_TO_MODEL_MAP[obj_type].objects.get(pk=data.obj_pk)

        audit_object = get_or_create_audit_obj(
            object_id=data.obj_pk,
            object_name=obj.name if obj_type != AuditObjectType.User else obj.username,
            object_type=obj_type,
        )
    else:
        operation_type = AuditLogOperationType.Create
        audit_object = get_audit_object_from_resp(
            response=response,
            obj_type=obj_type,
        )

    audit_operation = AuditOperation(
        name=f"{obj_type.capitalize()} {operation_type}d",
        operation_type=operation_type,
    )

    return audit_operation, audit_object


def rbac_case(
    path: list[str, ...],
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["rbac", "group"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Group,
                response=response,
            )

        case ["rbac", "group", group_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=group_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Group,
                response=response,
                data=data,
            )

        case ["rbac", "policy"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Policy,
                response=response,
            )

        case ["rbac", "policy", policy_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=policy_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Policy,
                response=response,
                data=data,
            )

        case ["rbac", "role"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Role,
                response=response,
            )

        case ["rbac", "role", role_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=role_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.Role,
                response=response,
                data=data,
            )

        case ["rbac", "user"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.User,
                response=response,
            )

        case ["rbac", "user", user_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=user_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.User,
                response=response,
                data=data,
            )

    return audit_operation, audit_object
