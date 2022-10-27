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

# pylint: disable=line-too-long

import fcntl
import json
import os
from collections import defaultdict

# isort: off
from ansible.errors import AnsibleError
from ansible.utils.vars import merge_hash
from ansible.plugins.action import ActionBase
from django.conf import settings

# isort: on
import adcm.init_django  # pylint: disable=unused-import
from cm import config
from cm.adcm_config import set_object_config
from cm.api import add_hc, get_hc
from cm.api_context import ctx
from cm.errors import AdcmEx
from cm.errors import raise_adcm_ex as err
from cm.models import (
    Action,
    ADCMEntity,
    CheckLog,
    Cluster,
    ClusterObject,
    GroupCheckLog,
    Host,
    HostProvider,
    JobLog,
    LogStorage,
    Prototype,
    ServiceComponent,
)
from cm.status_api import post_event

MSG_NO_CONFIG = (
    "There are no job related vars in inventory. It's mandatory for that module to have some"
    " info from context. During normal execution it runs with inventory and config.yaml generated"
    " by ADCM. Did you forget to pass them during debug? Bad Dobby!"
)
MSG_NO_CONTEXT = (
    "There are no context variable in job related vars in inventory. It's mandatory for that "
    "module to have some info from context. During normal execution it runs with inventory and "
    "config.yaml generated by ADCM. Did you forget to pass them during debug? Bad Dobby!"
)
MSG_WRONG_CONTEXT = 'Wrong context. Should be "{}", not "{}"'
MSG_WRONG_CONTEXT_ID = 'Wrong context. There are no "{}" in context'
MSG_NO_CLUSTER_CONTEXT = (
    "You are trying to change cluster state outside of cluster context. Cluster state can be "
    "changed in cluster's, service's or component's actions only. Bad Dobby!"
)
MSG_NO_CLUSTER_CONTEXT2 = (
    "You are trying to change service state outside of cluster context. Service state can be"
    " changed by service_name in cluster's actions only. Bad Dobby!"
)
MSG_NO_SERVICE_CONTEXT = (
    "You are trying to change unnamed service's state outside of service context."
    " Service state can be changed in service's actions only or in cluster's actions but"
    " with using service_name arg. Bad Dobby!"
)
MSG_MANDATORY_ARGS = "Arguments {} are mandatory. Bad Dobby!"
MSG_NO_ROUTE = "Incorrect combination of args. Bad Dobby!"
MSG_NO_SERVICE_NAME = "You must specify service name in arguments."
MSG_NO_MULTI_STATE_TO_DELETE = (
    "You try to delete absent multi_state. You should define missing_ok as True "
    "or choose an existing multi_state"
)


def job_lock(job_id):
    fname = os.path.join(settings.RUN_DIR, f'{job_id}/config.json')
    fd = open(fname, 'r', encoding=settings.ENCODING)
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)  # pylint: disable=I1101
        return fd
    except IOError as e:
        return err('LOCK_ERROR', e)


def job_unlock(fd):
    fd.close()


def check_context_type(task_vars, *context_type, err_msg=None):
    """
    Check context type. Check if inventory.json and config.json were passed
    and check if `context` exists in task variables, сheck if a context is of a given type.
    """
    if not task_vars:
        raise AnsibleError(MSG_NO_CONFIG)
    if 'context' not in task_vars:
        raise AnsibleError(MSG_NO_CONTEXT)
    if not isinstance(task_vars['context'], dict):
        raise AnsibleError(MSG_NO_CONTEXT)
    context = task_vars['context']
    if context['type'] not in context_type:
        if err_msg is None:
            err_msg = MSG_WRONG_CONTEXT.format(', '.join(context_type), context['type'])
        raise AnsibleError(err_msg)


def get_object_id_from_context(task_vars, id_type, *context_type, err_msg=None):
    """
    Get object id from context.
    """
    check_context_type(task_vars, *context_type, err_msg=err_msg)
    context = task_vars['context']
    if id_type not in context:
        raise AnsibleError(MSG_WRONG_CONTEXT_ID.format(id_type))
    return context[id_type]


class ContextActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = None
    _MANDATORY_ARGS = None

    def _wrap_call(self, func, *args):
        try:
            func(*args)
        except AdcmEx as e:
            return {'failed': True, 'msg': e.msg}
        return {'changed': True}

    def _check_mandatory(self):
        for arg in self._MANDATORY_ARGS:
            if arg not in self._task.args:
                raise AnsibleError(MSG_MANDATORY_ARGS.format(self._MANDATORY_ARGS))

    def _get_job_var(self, task_vars, name):
        try:
            return task_vars["job"][name]
        except KeyError as error:
            raise AnsibleError(MSG_NO_CLUSTER_CONTEXT) from error

    def _do_cluster(self, task_vars, context):
        raise NotImplementedError

    def _do_service_by_name(self, task_vars, context):
        raise NotImplementedError

    def _do_service(self, task_vars, context):
        raise NotImplementedError

    def _do_host(self, task_vars, context):
        raise NotImplementedError

    def _do_component(self, task_vars, context):
        raise NotImplementedError

    def _do_component_by_name(self, task_vars, context):
        raise NotImplementedError

    def _do_provider(self, task_vars, context):
        raise NotImplementedError

    def _do_host_from_provider(self, task_vars, context):
        raise NotImplementedError

    def run(self, tmp=None, task_vars=None):  # pylint: disable=too-many-branches
        self._check_mandatory()
        obj_type = self._task.args["type"]
        job_id = task_vars['job']['id']
        lock = job_lock(job_id)

        if obj_type == 'cluster':
            check_context_type(task_vars, 'cluster', 'service', 'component')
            res = self._do_cluster(
                task_vars, {'cluster_id': self._get_job_var(task_vars, 'cluster_id')}
            )
        elif obj_type == "service" and "service_name" in self._task.args:
            check_context_type(task_vars, 'cluster', 'service', 'component')
            res = self._do_service_by_name(
                task_vars, {'cluster_id': self._get_job_var(task_vars, 'cluster_id')}
            )
        elif obj_type == "service":
            check_context_type(task_vars, 'service', 'component')
            res = self._do_service(
                task_vars,
                {
                    'cluster_id': self._get_job_var(task_vars, 'cluster_id'),
                    'service_id': self._get_job_var(task_vars, 'service_id'),
                },
            )
        elif obj_type == "host" and "host_id" in self._task.args:
            check_context_type(task_vars, 'provider')
            res = self._do_host_from_provider(task_vars, {})
        elif obj_type == "host":
            check_context_type(task_vars, 'host')
            res = self._do_host(task_vars, {'host_id': self._get_job_var(task_vars, 'host_id')})
        elif obj_type == "provider":
            check_context_type(task_vars, 'provider', 'host')
            res = self._do_provider(
                task_vars, {'provider_id': self._get_job_var(task_vars, 'provider_id')}
            )
        elif obj_type == "component" and "component_name" in self._task.args:
            if "service_name" in self._task.args:
                check_context_type(task_vars, 'cluster', 'service', 'component')
                res = self._do_component_by_name(
                    task_vars,
                    {
                        'cluster_id': self._get_job_var(task_vars, 'cluster_id'),
                        'service_id': None,
                    },
                )
            else:
                check_context_type(task_vars, 'cluster', 'service', 'component')
                if task_vars['job'].get('service_id', None) is None:
                    raise AnsibleError(MSG_NO_SERVICE_NAME)
                res = self._do_component_by_name(
                    task_vars,
                    {
                        'cluster_id': self._get_job_var(task_vars, 'cluster_id'),
                        'service_id': self._get_job_var(task_vars, 'service_id'),
                    },
                )
        elif obj_type == "component":
            check_context_type(task_vars, 'component')
            res = self._do_component(
                task_vars, {'component_id': self._get_job_var(task_vars, 'component_id')}
            )
        else:
            raise AnsibleError(MSG_NO_ROUTE)

        result = super().run(tmp, task_vars)
        job_unlock(lock)
        return merge_hash(result, res)


# Helper functions for ansible plugins


def get_component_by_name(cluster_id, service_id, component_name, service_name):
    if service_id is not None:
        comp = ServiceComponent.obj.get(
            cluster_id=cluster_id, service_id=service_id, prototype__name=component_name
        )
    else:
        comp = ServiceComponent.obj.get(
            cluster_id=cluster_id,
            service__prototype__name=service_name,
            prototype__name=component_name,
        )
    return comp


def get_service_by_name(cluster_id, service_name):
    cluster = Cluster.obj.get(id=cluster_id)
    proto = Prototype.obj.get(type='service', name=service_name, bundle=cluster.prototype.bundle)
    return ClusterObject.obj.get(cluster=cluster, prototype=proto)


def _set_object_state(obj: ADCMEntity, state: str) -> ADCMEntity:
    obj.set_state(state, ctx.event)
    ctx.event.send_state()
    return obj


def set_cluster_state(cluster_id, state):
    obj = Cluster.obj.get(id=cluster_id)
    return _set_object_state(obj, state)


def set_host_state(host_id, state):
    obj = Host.obj.get(id=host_id)
    return _set_object_state(obj, state)


def set_component_state(component_id, state):
    obj = ServiceComponent.obj.get(id=component_id)
    return _set_object_state(obj, state)


def set_component_state_by_name(cluster_id, service_id, component_name, service_name, state):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _set_object_state(obj, state)


def set_provider_state(provider_id, state):
    obj = HostProvider.obj.get(id=provider_id)
    return _set_object_state(obj, state)


def set_service_state_by_name(cluster_id, service_name, state):
    obj = get_service_by_name(cluster_id, service_name)
    return _set_object_state(obj, state)


def set_service_state(cluster_id, service_id, state):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type='service')
    return _set_object_state(obj, state)


def _set_object_multi_state(obj: ADCMEntity, multi_state: str) -> ADCMEntity:
    obj.set_multi_state(multi_state, ctx.event)
    ctx.event.send_state()
    return obj


def set_cluster_multi_state(cluster_id, multi_state):
    obj = Cluster.obj.get(id=cluster_id)
    return _set_object_multi_state(obj, multi_state)


def set_service_multi_state_by_name(cluster_id, service_name, multi_state):
    obj = get_service_by_name(cluster_id, service_name)
    return _set_object_multi_state(obj, multi_state)


def set_service_multi_state(cluster_id, service_id, multi_state):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type='service')
    return _set_object_multi_state(obj, multi_state)


def set_component_multi_state_by_name(
    cluster_id, service_id, component_name, service_name, multi_state
):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _set_object_multi_state(obj, multi_state)


def set_component_multi_state(component_id, multi_state):
    obj = ServiceComponent.obj.get(id=component_id)
    return _set_object_multi_state(obj, multi_state)


def set_provider_multi_state(provider_id, multi_state):
    obj = HostProvider.obj.get(id=provider_id)
    return _set_object_multi_state(obj, multi_state)


def set_host_multi_state(host_id, multi_state):
    obj = Host.obj.get(id=host_id)
    return _set_object_multi_state(obj, multi_state)


def change_hc(job_id, cluster_id, operations):  # pylint: disable=too-many-branches
    '''
    For use in ansible plugin adcm_hc
    '''
    lock = job_lock(job_id)
    job = JobLog.objects.get(id=job_id)
    action = Action.objects.get(id=job.action_id)
    if action.hostcomponentmap:
        err('ACTION_ERROR', 'You can not change hc in plugin for action with hc_acl')

    cluster = Cluster.obj.get(id=cluster_id)
    hc = get_hc(cluster)
    for op in operations:
        service = ClusterObject.obj.get(cluster=cluster, prototype__name=op['service'])
        component = ServiceComponent.obj.get(
            cluster=cluster, service=service, prototype__name=op['component']
        )
        host = Host.obj.get(cluster=cluster, fqdn=op['host'])
        item = {
            'host_id': host.id,
            'service_id': service.id,
            'component_id': component.id,
        }
        if op['action'] == 'add':
            if item not in hc:
                hc.append(item)
            else:
                msg = 'There is already component "{}" on host "{}"'
                err('COMPONENT_CONFLICT', msg.format(component.prototype.name, host.fqdn))
        elif op['action'] == 'remove':
            if item in hc:
                hc.remove(item)
            else:
                msg = 'There is no component "{}" on host "{}"'
                err('COMPONENT_CONFLICT', msg.format(component.prototype.name, host.fqdn))
        else:
            err('INVALID_INPUT', f'unknown hc action "{op["action"]}"')

    add_hc(cluster, hc)
    job_unlock(lock)


def set_cluster_config(cluster_id, keys, value):
    cluster = Cluster.obj.get(id=cluster_id)
    return set_object_config(cluster, keys, value)


def set_host_config(host_id, keys, value):
    host = Host.obj.get(id=host_id)
    return set_object_config(host, keys, value)


def set_provider_config(provider_id, keys, value):
    provider = HostProvider.obj.get(id=provider_id)
    return set_object_config(provider, keys, value)


def set_service_config_by_name(cluster_id, service_name, keys, value):
    obj = get_service_by_name(cluster_id, service_name)
    return set_object_config(obj, keys, value)


def set_service_config(cluster_id, service_id, keys, value):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type='service')
    return set_object_config(obj, keys, value)


def set_component_config_by_name(cluster_id, service_id, component_name, service_name, keys, value):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return set_object_config(obj, keys, value)


def set_component_config(component_id, keys, value):
    obj = ServiceComponent.obj.get(id=component_id)
    return set_object_config(obj, keys, value)


def check_missing_ok(obj: ADCMEntity, multi_state: str, missing_ok):
    if missing_ok is False:
        if multi_state not in obj.multi_state:
            raise AnsibleError(MSG_NO_MULTI_STATE_TO_DELETE)


def _unset_object_multi_state(obj: ADCMEntity, multi_state: str, missing_ok) -> ADCMEntity:
    check_missing_ok(obj, multi_state, missing_ok)
    obj.unset_multi_state(multi_state, ctx.event)
    ctx.event.send_state()
    return obj


def unset_cluster_multi_state(cluster_id, multi_state, missing_ok):
    obj = Cluster.obj.get(id=cluster_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_service_multi_state_by_name(cluster_id, service_name, multi_state, missing_ok):
    obj = get_service_by_name(cluster_id, service_name)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_service_multi_state(cluster_id, service_id, multi_state, missing_ok):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type='service')
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_component_multi_state_by_name(
    cluster_id, service_id, component_name, service_name, multi_state, missing_ok
):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_component_multi_state(component_id, multi_state, missing_ok):
    obj = ServiceComponent.obj.get(id=component_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_provider_multi_state(provider_id, multi_state, missing_ok):
    obj = HostProvider.obj.get(id=provider_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_host_multi_state(host_id, multi_state, missing_ok):
    obj = Host.obj.get(id=host_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def log_group_check(group: GroupCheckLog, fail_msg: str, success_msg: str):
    logs = CheckLog.objects.filter(group=group).values('result')
    result = all(log['result'] for log in logs)

    if result:
        msg = success_msg
    else:
        msg = fail_msg

    group.message = msg
    group.result = result
    group.save()


def log_check(job_id: int, group_data: dict, check_data: dict) -> CheckLog:
    lock = job_lock(job_id)
    job = JobLog.obj.get(id=job_id)
    if job.status != config.Job.RUNNING:
        err('JOB_NOT_FOUND', f'job #{job.pk} has status "{job.status}", not "running"')

    group_title = group_data.pop('title')

    if group_title:
        group, _ = GroupCheckLog.objects.get_or_create(job=job, title=group_title)
    else:
        group = None

    check_data.update({'job': job, 'group': group})
    cl = CheckLog.objects.create(**check_data)

    if group is not None:
        group_data.update({'group': group})
        log_group_check(**group_data)

    ls, _ = LogStorage.objects.get_or_create(job=job, name='ansible', type='check', format='json')

    post_event(
        'add_job_log',
        'job',
        job_id,
        {
            'id': ls.pk,
            'type': ls.type,
            'name': ls.name,
            'format': ls.format,
        },
    )
    job_unlock(lock)
    return cl


def get_check_log(job_id: int):
    data = []
    group_subs = defaultdict(list)

    for cl in CheckLog.objects.filter(job_id=job_id):
        group = cl.group
        if group is None:
            data.append(
                {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result}
            )
        else:
            if group not in group_subs:
                data.append(
                    {
                        'title': group.title,
                        'type': 'group',
                        'message': group.message,
                        'result': group.result,
                        'content': group_subs[group],
                    }
                )
            group_subs[group].append(
                {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result}
            )
    return data


def finish_check(job_id: int):
    data = get_check_log(job_id)
    if not data:
        return

    job = JobLog.objects.get(id=job_id)
    LogStorage.objects.filter(job=job, name='ansible', type='check', format='json').update(
        body=json.dumps(data)
    )

    GroupCheckLog.objects.filter(job=job).delete()
    CheckLog.objects.filter(job=job).delete()
