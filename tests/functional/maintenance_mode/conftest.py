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

"""
conftest.py for maintenance mode related tests
"""

# pylint: disable=redefined-outer-name

import os
from pathlib import Path
from typing import Iterable, Set, Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Host, Provider

from tests.functional.tools import AnyADCMObject
from tests.library.api.client import APIClient
from tests.library.utils import get_hosts_fqdn_representation

BUNDLES_DIR = Path(os.path.dirname(__file__)) / 'bundles'

MM_IS_ON = "ON"
MM_IS_OFF = "OFF"
MM_ALLOWED = True
MM_NOT_ALLOWED = False

START_IMPOSSIBLE_REASONS = {
    "The Action is not available. One or more hosts in 'Maintenance mode'",
    "The Action is not available. Host in 'Maintenance mode'",
}

PROVIDER_NAME = 'Test Default Provider'
CLUSTER_WITH_MM_NAME = 'Test Cluster WITH Maintenance Mode'
CLUSTER_WITHOUT_MM_NAME = 'Test Cluster WITHOUT Maintenance Mode'
DEFAULT_SERVICE_NAME = 'test_service'
ANOTHER_SERVICE_NAME = 'another_service'
FIRST_COMPONENT = 'first_component'
SECOND_COMPONENT = 'second_component'


@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Upload bundle and create default provider"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'default_provider')
    return bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
def hosts(provider) -> Tuple[Host, Host, Host, Host, Host, Host]:
    """Create 6 hosts from the default bundle"""
    return tuple(provider.host_create(f'test-host-{i}') for i in range(6))


@pytest.fixture()
def cluster_with_mm(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_allowed')
    cluster = bundle.cluster_create(CLUSTER_WITH_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


@pytest.fixture(params=['cluster_mm_disallowed'], ids=lambda x: x.strip('cluster_'))
def cluster_without_mm(request, sdk_client_fs: ADCMClient):
    """
    Upload cluster bundle with disallowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / request.param)
    cluster = bundle.cluster_create(CLUSTER_WITHOUT_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


def turn_mm_on(api_client: APIClient, host: Host):
    """Turn maintenance mode "on" on host"""
    with allure.step(f'Turn MM "on" on host {host.fqdn}'):
        api_client.host.change_maintenance_mode(host.id, MM_IS_ON).check_code(200)
        host.reread()
        assert (
            actual_mm := host.maintenance_mode
        ) == MM_IS_ON, f'Maintenance mode of host {host.fqdn} should be {MM_IS_ON}, not {actual_mm}'


def turn_mm_off(api_client: APIClient, host: Host):
    """Turn maintenance mode "off" on host"""
    with allure.step(f'Turn MM "off" on host {host.fqdn}'):
        api_client.host.change_maintenance_mode(host.id, MM_IS_OFF).check_code(200)
        host.reread()
        assert (
            actual_mm := host.maintenance_mode
        ) == MM_IS_OFF, f'Maintenance mode of host {host.fqdn} should be {MM_IS_OFF}, not {actual_mm}'


def add_hosts_to_cluster(cluster: Cluster, hosts: Iterable[Host]):
    """Add hosts to cluster"""
    with allure.step(f'Add hosts to the cluster "{cluster.name}": {get_hosts_fqdn_representation(hosts)}'):
        for host in hosts:
            cluster.host_add(host)


def remove_hosts_from_cluster(cluster: Cluster, hosts: Iterable[Host]):
    """Remove hosts from cluster"""
    with allure.step(f'Add hosts to the cluster "{cluster.name}": {get_hosts_fqdn_representation(hosts)}'):
        for host in hosts:
            cluster.host_delete(host)


def check_hosts_mm_is(maintenance_mode: str, *hosts: Host):
    """Check that MM of hosts is equal to the expected one"""
    with allure.step(
        f'Check that "maintenance_mode" is equal to "{maintenance_mode}" '
        f'on hosts: {get_hosts_fqdn_representation(hosts)}'
    ):
        for host in hosts:
            host.reread()
        hosts_in_wrong_mode = tuple(host for host in hosts if host.maintenance_mode != maintenance_mode)
        if len(hosts_in_wrong_mode) == 0:
            return
        raise AssertionError(
            'Some hosts have incorrect value of "maintenance_mode" flag.\n'
            f'Hosts: {get_hosts_fqdn_representation(hosts_in_wrong_mode)}'
        )


def check_mm_availability(is_mm_available: bool, *hosts: Host):
    """Check that MM change is allowed/disallowed for the given hosts"""
    with allure.step(
        f'Check that "is_maintenance_mode_available" is {is_mm_available} '
        f'on hosts: {get_hosts_fqdn_representation(hosts)}'
    ):
        for host in hosts:
            host.reread()
        hosts_in_wrong_mode = tuple(host for host in hosts if host.is_maintenance_mode_available is not is_mm_available)
        if len(hosts_in_wrong_mode) == 0:
            return
        raise AssertionError(
            'Some hosts have incorrect value of "is_maintenance_mode_available" flag.\n'
            f'Hosts: {get_hosts_fqdn_representation(hosts_in_wrong_mode)}'
        )


def get_enabled_actions_names(adcm_object: AnyADCMObject) -> Set[str]:
    """Get actions that aren't disabled by maintenance mode"""
    return {
        action.name
        for action in adcm_object.action_list()
        if action.start_impossible_reason not in START_IMPOSSIBLE_REASONS
    }


def get_disabled_actions_names(adcm_object: AnyADCMObject) -> Set[str]:
    """Get actions disabled because of maintenance mode"""
    return {
        action.name
        for action in adcm_object.action_list()
        if action.start_impossible_reason in START_IMPOSSIBLE_REASONS
    }
