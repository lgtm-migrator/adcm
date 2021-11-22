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

"""RBAC models"""

import importlib

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.db import models
from guardian.models import UserObjectPermission

from adwp_base.errors import raise_AdwpEx as err
from cm.models import Bundle


class Role(models.Model):
    """
    Role is a list of Django permissions.
    Role can be assigned to user or to group of users
    Also Role can have childs and so produce acyclic graph of linked roles
    """

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    childs = models.ManyToManyField("self", symmetrical=False, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    module_name = models.CharField(max_length=32)
    class_name = models.CharField(max_length=32)
    init_params = models.JSONField(default=dict)
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, null=True, default=None)
    __obj__ = None

    class Meta:
        unique_together = (('name', 'bundle',))

    def get_role_obj(self):
        """Returns object with related role based on classes from roles.py"""
        try:
            role_module = importlib.import_module(self.module_name)
        except ModuleNotFoundError:
            err('ROLE_MODULE_ERROR', f'No module named "{self.module_name}"')
        try:
            role_class = getattr(role_module, self.class_name)
        except AttributeError:
            msg = f'No class named "{self.class_name}" in module "{self.module_name}"'
            err('ROLE_CLASS_ERROR', msg)

        return role_class(**self.init_params)  # pylint: disable=E1134

    def filter(self):
        """filter out objects sutable for role"""
        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()
        return self.__obj__.filter()

    def apply(self, policy: 'Policy', user: User, group: Group = None):
        """apply policy to user and/or group"""
        if self.__obj__ is None:
            self.__obj__ = self.get_role_obj()
        return self.__obj__.apply(policy, self, user, group)

    def get_permissions(self, role: 'Role' = None):
        """Recursively get permissions of role and all her childs"""
        role_list = []
        perm_list = []
        if role is None:
            role = self

        def get_perm(role, perm_list, role_list):
            if role in role_list:
                return
            role_list.append(role)
            for p in role.permissions.all():
                if p not in perm_list:
                    perm_list.append(p)
            for child in role.childs.all():
                get_perm(child, perm_list, role_list)

        get_perm(role, perm_list, role_list)
        return perm_list


class RoleMigration(models.Model):
    """Keep version of last role upgrade"""

    version = models.PositiveIntegerField(primary_key=True)
    date = models.DateTimeField(auto_now=True)


class PolicyObject(models.Model):
    """Reference to any model for Policy"""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id'], name='unique_policy_object'
            )
        ]


class PolicyPermission(models.Model):
    """Reference to Policy model level Permissions"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, default=None)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, null=True, default=None)


class Policy(models.Model):
    """Policy connect role, users and (maybe) objects"""

    name = models.CharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    object = models.ManyToManyField(PolicyObject, blank=True)
    user = models.ManyToManyField(User, blank=True)
    group = models.ManyToManyField(Group, blank=True)
    model_perm = models.ManyToManyField(PolicyPermission, blank=True)
    object_perm = models.ManyToManyField(UserObjectPermission, blank=True)

    def remove_permissions(self):
        for pp in self.model_perm.all():
            if pp.user:
                pp.user.user_permissions.remove(pp.permission)
            if pp.group:
                pp.group.permissions.remove(pp.permission)
            pp.delete()
        for pp in self.object_perm.all():
            pp.delete()

    def get_objects(self):
        obj_list = []
        for obj in self.object.all():
            obj_list.append(obj.object)
        return obj_list

    def filter(self):
        return self.role.filter()

    @atomic
    def apply(self):
        """This function apply role over"""
        self.remove_permissions()
        for user in self.user.all():
            self.role.apply(self, user)
        for group in self.group.all():
            self.role.apply(self, None, group=group)


class UserProfile(models.Model):
    """Arbitrary information about user for frontend"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    profile = models.JSONField(default=str)
