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
Test designed to check MM state calculation logic for services/components
"""

import allure
import pytest

from adcm_client.objects import Cluster, ADCMClient
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    ANOTHER_SERVICE_NAME,
    DEFAULT_SERVICE_NAME,
    MM_IS_OFF,
    MM_IS_ON,
    add_hosts_to_cluster,
    check_mm_is,
    set_maintenance_mode, BUNDLES_DIR, get_enabled_actions_names, get_disabled_actions_names,
)
from tests.library.assertions import sets_are_equal


# pylint: disable=redefined-outer-name

@pytest.fixture()
def cluster_with_mm(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_allowed')
    cluster = bundle.cluster_create("Cluster with mm")
    cluster.service_add(name="first_service")
    return cluster


@pytest.fixture()
def cluster_with_action_on_service_component(sdk_client_fs: ADCMClient) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_service_component_actions")
    cluster = bundle.cluster_create("Cluster actions")
    cluster.service_add(name="first_service")
    return cluster


@only_clean_adcm
def test_mm_state_service(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on services and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    second_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for service'):
        set_maintenance_mode(api_client=api_client, adcm_object=second_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, second_service)
        check_mm_is(MM_IS_OFF, first_host, second_host, first_component, second_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_component, second_component, first_service, second_service)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_service, maintenance_mode=MM_IS_OFF)
        check_mm_is(
            MM_IS_OFF, first_host, second_host, first_component, second_component, first_service, second_service
        )

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service)
        check_mm_is(MM_IS_OFF, first_host, second_host, second_service)


@only_clean_adcm
def test_mm_state_component(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on components and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for components'):
        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_component)
        check_mm_is(MM_IS_OFF, first_host, second_host, second_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_component, second_component, first_service)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_host, second_host, first_component, second_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, second_component)
        check_mm_is(MM_IS_OFF, first_host, second_host, first_component, first_service)


@only_clean_adcm
def test_mm_state_host(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on components and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for hosts'):
        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_host, first_component)
        check_mm_is(MM_IS_OFF, first_service, second_host, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_host, first_component, second_host, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_service, first_host, first_component, second_host, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, second_host, second_component)


def test_mm_state_with_issue(api_client, cluster_with_issue_on_service_component):
    """
    Test to check maintenance_mode on components with issue
    first_service and second_component have issue
    """
    first_service = cluster_with_issue_on_service_component.service(name="first_service")
    first_component = first_service.component(name="first_component")
    second_component = first_service.component(name="second_component")

    with allure.step('Check MM state calculation logic for component with issue'):
        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, second_component)
        check_mm_is(MM_IS_OFF, first_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, second_component, first_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_service, first_component, second_component)

    with allure.step('Check MM state calculation logic for service with issue'):
        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service)
        check_mm_is(MM_IS_OFF, first_component, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_service, first_component, second_component)


def test_mm_state_with_action(api_client, cluster_with_action_on_service_component, hosts):
    """
    Test to check maintenance_mode on components with issue
    first_service and second_component have issue
    """
    expected_enabled = {'default_action'} | {
        f'{obj_type}_action_allowed' for obj_type in ('cluster', 'service', 'component')
    }
    expected_disabled = {f'{obj_type}_action_disallowed' for obj_type in ('cluster', 'service', 'component')}

    host_in_mm, regular_host, *_ = hosts
    cluster = cluster_with_action_on_service_component
    service = cluster.service()
    component = service.component()

    add_hosts_to_cluster(cluster, (host_in_mm, regular_host))
    cluster.hostcomponent_set((host_in_mm, component), (regular_host, component))

    with allure.step('Check MM state calculation logic for service with action'):
        set_maintenance_mode(api_client=api_client, adcm_object=service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, service, component)
        check_mm_is(MM_IS_OFF, host_in_mm, regular_host)

    with allure.step('Check MM state calculation logic for component with action'):
        set_maintenance_mode(api_client=api_client, adcm_object=component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, service, component)
        check_mm_is(MM_IS_OFF, host_in_mm, regular_host)

    with allure.step("Switch service and component to MM 'OFF' and check logic"):
        set_maintenance_mode(api_client=api_client, adcm_object=service, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=component, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, service, component, host_in_mm, regular_host)

    with allure.step("Switch host to MM 'ON' and check actions"):
        set_maintenance_mode(api_client=api_client, adcm_object=host_in_mm, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, host_in_mm)
        check_mm_is(MM_IS_OFF, service, component, regular_host)

        enabled_actions = get_enabled_actions_names(regular_host)
        disabled_actions = get_disabled_actions_names(regular_host)

    with allure.step('Check that correct actions are enabled/disabled on the host'):
        sets_are_equal(enabled_actions, expected_enabled, f'Incorrect actions are enabled on host {regular_host.fqdn}')
        sets_are_equal(
            disabled_actions, expected_disabled, f'Incorrect actions are disabled on host {regular_host.fqdn}'
        )
