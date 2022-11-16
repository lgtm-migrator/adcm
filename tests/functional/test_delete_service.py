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

"""Tests for service delete method"""

import allure
from adcm_client.objects import ADCMClient, Cluster, Provider
from adcm_pytest_plugin.utils import get_data_dir

from tests.library.assertions import expect_api_error, expect_no_api_error
from tests.library.errorcodes import SERVICE_CONFLICT, SERVICE_DELETE_ERROR


def test_delete_service(sdk_client_fs: ADCMClient):
    """
    If host has NO component, then we can simply remove it from cluster.
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "default"))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster.reread()
    with allure.step("Ensure there's a concern on cluster from service's config"):
        assert len(cluster.concerns()) > 0, "There should be a concern on cluster from config of the service"
    with allure.step("Delete service"):
        service.delete()
    with allure.step("Ensure that concern is gone from cluster after service removal"):
        cluster.reread()
        assert len(cluster.concerns()) == 0, "Concern on cluster should be removed alongside with the service"


def test_forbid_service_deletion_no_action(sdk_client_fs: ADCMClient, generic_provider: Provider) -> None:
    cluster = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "forbidden_to_delete")).cluster_create(
        "Cluster with forbidden to delete services"
    )

    with allure.step("Check service required for cluster can't be deleted"):
        service = cluster.service_add(name="required_service")
        expect_api_error("delete required service", operation=service.delete, err_=SERVICE_DELETE_ERROR)

    with allure.step("Check service mapped to hosts can't be deleted"):
        service = cluster.service_add(name="with_component")
        cluster.hostcomponent_set((cluster.host_add(generic_provider.host_create("host-fqdn")), service.component()))
        expect_api_error("delete mapped service without action", operation=service.delete)

    with allure.step("Check service that is imported can't be deleted"):
        importer: Cluster = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "with_import")).cluster_create(
            "Importer Cluster"
        )
        importer.bind(service)
        expect_api_error("delete service with export", operation=service.delete, err_=SERVICE_CONFLICT)

    with allure.step("Check unmapped service can't be deleted when not in 'created' state"):
        service = cluster.service_add(name="state_change")
        service.action().run().wait()
        service.reread()
        assert service.state != "created"
        expect_api_error("delete service not in 'created' state", operation=service.delete, err_=SERVICE_DELETE_ERROR)


def test_service_deletion_with_action(sdk_client_fs: ADCMClient, generic_provider: Provider) -> None:
    cluster = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "with_action")).cluster_create(
        "Cluster with service remove actions"
    )

    with allure.step("Check service required for cluster can't be deleted"):
        service = cluster.service_add(name="required_service")
        expect_api_error("delete required service", operation=service.delete, err_=SERVICE_DELETE_ERROR)
        _check_actions_amount(sdk_client_fs, 0)

    with allure.step("Check unmapped service with bonded action can be simply deleted"):
        service = cluster.service_add(name="with_component")
        service.delete()
        _check_actions_amount(sdk_client_fs, 0)

    with allure.step("Check unmapped service not in 'created' state can be deleted with action"):
        service = cluster.service_add(name="state_change")
        service.action(name="change_state").run().wait()
        expect_no_api_error("Delete service with 'remove' action", operation=service.delete)
        _wait_all_tasks_succeed(sdk_client_fs, 2)

    with allure.step("Check that service that others depend on can't be deleted"):
        service_with_component = cluster.service_add(name="with_component")
        dependent_service = cluster.service_add(name="with_dependent_component")
        host = cluster.host_add(generic_provider.host_create("some-fqdn"))
        cluster.hostcomponent_set((host, service_with_component.component()), (host, dependent_service.component()))
        expect_api_error(
            "delete service with 'requires' component", operation=service_with_component.delete, err_=SERVICE_CONFLICT
        )

    with allure.step("Check that delete dependant service first is allowed"):
        expect_no_api_error("delete dependant service", operation=dependent_service.delete)
        _wait_all_tasks_succeed(sdk_client_fs, 3)
        expect_no_api_error("delete mapped service", operation=service_with_component.delete)
        _wait_all_tasks_succeed(sdk_client_fs, 4)

    with allure.step("Check that imported service can't be deleted even with action"):
        importer: Cluster = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "with_import")).cluster_create(
            "Importer Cluster"
        )
        service = cluster.service_add(name="with_component")
        importer.bind(service)
        expect_api_error("delete service with export", operation=service.delete, err_=SERVICE_CONFLICT)


@allure.step("Check amount of jobs is {expected_amount} and all tasks finish successfully")
def _wait_all_tasks_succeed(client: ADCMClient, expected_amount: int):
    jobs = client.job_list()
    assert _check_actions_amount(client, expected_amount)
    assert all(job.task().wait() == "success" for job in jobs)


def _check_actions_amount(client: ADCMClient, expected_amount: int) -> None:
    assert (
        actual := len(client.job_list())
    ) == expected_amount, f"Expected jobs amount should be {expected_amount}.\nActual: {actual}"
