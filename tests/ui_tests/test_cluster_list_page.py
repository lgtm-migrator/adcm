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

import os

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Provider,
)
from adcm_pytest_plugin import utils

from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.cluster.page import (
    ClusterImportPage,
    ClusterConfigPage,
    ClusterMainPage,
    ClusterHostPage,
    ClusterServicesPage,
    ClusterComponentsPage,
    ComponentsHostRowInfo,
    ClusterStatusPage,
    ImportItemInfo,
    ClusterActionPage,
)
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.host.page import (
    HostMainPage,
    HostConfigPage,
)
from tests.ui_tests.app.page.service.page import (
    ServiceMainPage,
    ServiceConfigPage,
    ServiceImportPage,
)
from tests.ui_tests.utils import wait_and_assert_ui_info, check_host_value

BUNDLE_COMMUNITY = "cluster_community"
BUNDLE_ENTERPRISE = "cluster_enterprise"
BUNDLE_IMPORT = "cluster_to_import"
BUNDLE_UPGRADE = "upgradable_cluster"
BUNDLE_REQUIRED_FIELDS = "cluster_and_service_with_required_string"
BUNDLE_WITH_SERVICES = "cluster_with_services"
CLUSTER_NAME = "Test cluster"
SERVICE_NAME = "test_service"
PROVIDER_NAME = 'test_provider'
HOST_NAME = 'test-host'
PROVIDER_WITH_ISSUE_NAME = 'provider_with_issue'
COMPONENT_NAME = "first"
BUNDLE_WITH_REQUIRED_FIELDS = "cluster_required_fields"


# pylint: disable=redefined-outer-name,no-self-use,unused-argument
pytestmark = pytest.mark.usefixtures("login_to_adcm_over_api")


@pytest.fixture()
def create_community_cluster(sdk_client_fs: ADCMClient):
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.fixture()
def create_community_cluster_with_service(sdk_client_fs: ADCMClient):
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME)


@pytest.fixture()
def create_import_cluster_with_service(sdk_client_fs: ADCMClient):
    params = {
        "import_cluster_name": "Import cluster",
        "import_service_name": "Pre-uploaded Dummy service to import",
    }
    with allure.step("Create main cluster"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
        cluster_main = bundle.cluster_create(name=CLUSTER_NAME)
        service_main = cluster_main.service_add(name=SERVICE_NAME)
    with allure.step("Create cluster to import"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_IMPORT)
        cluster_import = bundle.cluster_create(name=params["import_cluster_name"])
        service_import = cluster_import.service_add(name=params["import_service_name"])
        return cluster_main, service_main, cluster_import, service_import


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@pytest.fixture()
@allure.title("Create provider from uploaded bundle")
def upload_and_create_provider(provider_bundle) -> Provider:
    return provider_bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
def create_community_cluster_with_host(app_fs, sdk_client_fs: ADCMClient, upload_and_create_provider, create_host):
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    host = cluster.host_add(create_host)
    return cluster, host


@pytest.fixture()
def create_community_cluster_with_host_and_service(sdk_client_fs: ADCMClient, create_host):
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    cluster.service_add(name=SERVICE_NAME)
    cluster.host_add(create_host)
    return cluster, create_host


@pytest.fixture()
@allure.title("Create host")
def create_host(upload_and_create_provider):
    """Create default host using API"""
    provider = upload_and_create_provider
    return provider.host_create(HOST_NAME)


@allure.title("Check all values in host info")
def check_components_host_info(host_info: ComponentsHostRowInfo, name: str, components: str):
    """Check all values in host info"""
    check_host_value('name', host_info.name, name)
    check_host_value('components', host_info.components, components)


class TestClusterListPage:
    @pytest.mark.smoke()
    @pytest.mark.parametrize(
        "bundle_archive",
        [
            pytest.param(utils.get_data_dir(__file__, BUNDLE_COMMUNITY), id="community"),
            pytest.param(utils.get_data_dir(__file__, BUNDLE_ENTERPRISE), id="enterprise"),
        ],
        indirect=True,
    )
    def test_check_cluster_list_page_with_cluster_creating(self, app_fs, bundle_archive):
        edition = bundle_archive.split("cluster_")[2][:-4]
        cluster_params = {
            "bundle": f"test_cluster 1.5 {edition}",
            "description": "Test",
            "state": "created",
        }
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Check no cluster rows"):
            assert len(cluster_page.table.get_all_rows()) == 0, "There should be no row with clusters"
        cluster_page.create_cluster(
            bundle_archive, cluster_params['description'], is_license=bool(edition == "enterprise")
        )
        with allure.step("Check uploaded cluster"):
            assert len(cluster_page.table.get_all_rows()) == 1, "There should be 1 row with cluster"
            uploaded_cluster = cluster_page.get_cluster_info_from_row(0)
            assert cluster_params['bundle'] == uploaded_cluster['bundle'], (
                f"Cluster bundle should be {cluster_params['bundle']} and " f"not {uploaded_cluster['bundle']}"
            )
            assert cluster_params['description'] == uploaded_cluster['description'], (
                f"Cluster description should be {cluster_params['description']} and "
                f"not {uploaded_cluster['description']}"
            )
            assert cluster_params['state'] == uploaded_cluster['state'], (
                f"Cluster state should be {cluster_params['state']} " f"and not {uploaded_cluster['state']}"
            )

    def test_check_cluster_list_page_pagination(self, sdk_client_fs: ADCMClient, app_fs):
        with allure.step("Create 11 clusters"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            for i in range(11):
                bundle.cluster_create(name=f"Test cluster {i}")
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.close_info_popup()
        cluster_page.table.check_pagination(second_page_item_amount=1)

    @pytest.mark.smoke()
    @pytest.mark.usefixtures("create_community_cluster")
    def test_check_cluster_list_page_action_run(self, app_fs):
        params = {"action_name": "test_action", "expected_state": "installed"}
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        with cluster_page.wait_cluster_state_change(row):
            cluster_page.run_action_in_cluster_row(row, params["action_name"])
        with allure.step("Check cluster state has changed"):
            assert (
                cluster_page.get_cluster_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success cluster job"):
            assert (
                cluster_page.header.get_success_job_amount_from_header() == "1"
            ), "There should be 1 success cluster job in header"

    @pytest.mark.smoke()
    def test_check_cluster_list_page_import_run(self, create_import_cluster_with_service, app_fs):
        cluster, _, _, _ = create_import_cluster_with_service
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.get_row_by_cluster_name(CLUSTER_NAME)
        cluster_page.click_import_btn_in_row(row)
        import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        import_page.wait_page_is_opened()
        with allure.step("Check import on import page"):
            assert len(import_page.get_import_items()) == 1, "Cluster import page should contain 1 import"

    @pytest.mark.smoke()
    def test_check_cluster_list_page_open_cluster_config(self, app_fs, create_community_cluster):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        cluster_page.click_config_button_in_row(row)
        ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    @pytest.mark.smoke()
    def test_check_cluster_list_page_open_cluster_main(self, app_fs, create_community_cluster):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        cluster_page.click_cluster_name_in_row(row)
        ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    @pytest.mark.smoke()
    @pytest.mark.usefixtures("create_community_cluster")
    def test_check_cluster_list_page_delete_cluster(self, app_fs):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        with cluster_page.table.wait_rows_change():
            cluster_page.delete_cluster_by_row(row)
        with allure.step("Check there are no rows"):
            assert len(cluster_page.table.get_all_rows()) == 0, "Cluster table should be empty"


class TestClusterMainPage:
    @pytest.mark.smoke()
    def test_check_cluster_main_page_open_by_tab(self, app_fs, create_community_cluster):
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_config_page.open_main_tab()
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_main_page.wait_page_is_opened()
        cluster_main_page.check_all_elements()

    def test_check_cluster_admin_page_open_by_toolbar(self, app_fs, create_community_cluster):
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_check_cluster_main_page_open_by_toolbar(self, app_fs, create_community_cluster):
        params = {"cluster_list_name": "CLUSTERS"}
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.click_link_by_name(params["cluster_list_name"])
        ClusterListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        cluster_import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_import_page.toolbar.click_link_by_name(CLUSTER_NAME)
        cluster_main_page.wait_page_is_opened()

    def test_run_upgrade_on_cluster_page_by_toolbar(self, sdk_client_fs, app_fs):
        params = {
            "upgrade_cluster_name": "upgrade cluster",
            "upgrade": "upgrade 2",
            "state": "upgradated",
        }
        with allure.step("Create main cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            bundle.cluster_create(name=CLUSTER_NAME)
        with allure.step("Create cluster to upgrade"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_UPGRADE)
            cluster_to_upgrade = bundle.cluster_create(name=params["upgrade_cluster_name"])
        main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, cluster_to_upgrade.id).open()
        main_page.toolbar.run_upgrade(params["upgrade_cluster_name"], params["upgrade"])
        with allure.step("Check that cluster has been upgraded"):
            cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
            row = cluster_page.get_row_by_cluster_name(params["upgrade_cluster_name"])
            assert (
                cluster_page.get_cluster_state_from_row(row) == params["state"]
            ), f"Cluster state should be {params['state']}"

    def test_check_cluster_run_action_on_cluster_page_by_toolbar(self, app_fs, create_community_cluster):
        params = {"action_name": "test_action"}
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.run_action(CLUSTER_NAME, params["action_name"])
        with allure.step("Check success job"):
            assert (
                cluster_main_page.header.get_in_progress_job_amount_from_header() == "1"
            ), "There should be 1 in progress job in header"


class TestClusterServicePage:
    @pytest.mark.smoke()
    def test_check_cluster_service_page_open_by_tab(self, app_fs, create_community_cluster):
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_config_page.open_services_tab()
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_service_page.wait_page_is_opened()
        cluster_service_page.check_all_elements()

    @pytest.mark.smoke()
    def test_check_create_and_open_service_page_from_cluster_page(self, app_fs, create_community_cluster):
        params = {"service_name": "test_service - 1.2"}
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_service_page.add_service_by_name(params["service_name"])
        service_row = cluster_service_page.table.get_all_rows()[0]
        service_row.click()
        ServiceMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id, 1).wait_page_is_opened()

    def test_check_required_fields_from_cluster_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        params = {"issue_name": "Configuration"}
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
        cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_list_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_list_page.table.get_all_rows()[0]
        cluster_list_page.click_on_issue_by_name(row, params["issue_name"])
        ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).wait_page_is_opened()

    def test_check_required_fields_from_service_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        params = {"issue_name": "Configuration"}
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
        cluster = bundle.cluster_create(name=CLUSTER_NAME).service_add(name=SERVICE_NAME)
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_on_issue_by_name(row, params["issue_name"])
        ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, 1).wait_page_is_opened()

    @pytest.mark.smoke()
    def test_check_actions_from_service_list_page(self, app_fs, create_community_cluster_with_service):
        params = {"action_name": "test_action", "expected_state": "installed"}

        cluster, _ = create_community_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        with cluster_service_page.wait_service_state_change(row):
            cluster_service_page.run_action_in_service_row(row, params["action_name"])
        with allure.step("Check service state has changed"):
            assert (
                cluster_service_page.get_service_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success service job"):
            assert (
                cluster_service_page.header.get_success_job_amount_from_header() == "1"
            ), "There should be 1 success service job in header"

    def test_check_service_list_page_import_run(self, app_fs, create_import_cluster_with_service):
        cluster, service, _, _ = create_import_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_import_btn_in_row(row)
        import_page = ServiceImportPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id)
        import_page.wait_page_is_opened()
        with allure.step("Check import on import page"):
            assert len(import_page.get_import_items()) == 1, "Service import page should contain 1 import"

    def test_check_service_list_page_open_service_config(self, app_fs, create_community_cluster_with_service):
        cluster, service = create_community_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_config_btn_in_row(row)
        ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).wait_page_is_opened()

    def test_check_pagination_on_service_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_SERVICES)
        cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_service_page.add_service_by_name(service_name="All")
        cluster_service_page.table.check_pagination(second_page_item_amount=2)


class TestClusterHostPage:
    @pytest.mark.smoke()
    def test_check_required_fields_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        cluster, _ = create_community_cluster_with_service
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_main_page.open_hosts_tab()
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.check_all_elements()

    @pytest.mark.smoke()
    @pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, "provider")], indirect=True)
    def test_check_create_host_and_hostprovider_from_cluster_host_page(
        self, app_fs, bundle_archive, create_community_cluster_with_service
    ):
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.click_add_host_btn(is_not_first_host=False)
        new_provider_name = cluster_host_page.host_popup.create_provider_and_host(bundle_archive, HOST_NAME)
        expected_values = {
            'fqdn': HOST_NAME,
            'provider': new_provider_name,
            'cluster': None,
            'state': 'created',
        }
        wait_and_assert_ui_info(
            expected_values,
            cluster_host_page.get_host_info_from_row,
            get_info_kwargs={'table_has_cluster_column': False},
        )

    @pytest.mark.smoke()
    @pytest.mark.usefixtures("upload_and_create_provider")
    def test_check_create_host_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        expected_values = {
            'fqdn': HOST_NAME,
            'provider': PROVIDER_NAME,
            'cluster': None,
            'state': 'created',
        }
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.click_add_host_btn(is_not_first_host=False)
        cluster_host_page.host_popup.create_host(HOST_NAME)
        wait_and_assert_ui_info(
            expected_values,
            cluster_host_page.get_host_info_from_row,
            get_info_kwargs={'table_has_cluster_column': False},
        )
        host_row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_on_host_name_in_host_row(host_row)
        HostMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, 1).wait_page_is_opened()

    @pytest.mark.usefixtures('create_host')
    def test_check_create_host_error_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.close_info_popup()
        cluster_host_page.click_add_host_btn()
        cluster_host_page.host_popup.create_host(HOST_NAME)
        with allure.step("Check error message"):
            assert (
                cluster_host_page.get_info_popup_text() == '[ CONFLICT ] HOST_CONFLICT -- duplicate host'
            ), "No message about host duplication"

    @pytest.mark.parametrize('provider_bundle', [PROVIDER_WITH_ISSUE_NAME], indirect=True)
    def test_check_open_host_issue_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        params = {"issue_name": "Configuration"}
        cluster, host = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_on_issue_by_name(row, params["issue_name"])
        HostConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, host.id).wait_page_is_opened()

    def test_check_host_action_run_from_cluster(self, app_fs, create_community_cluster_with_host):
        params = {"action_name": "test_action", "expected_state": "installed"}
        cluster, _ = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        with cluster_host_page.wait_host_state_change(row):
            cluster_host_page.run_action_in_host_row(row, params["action_name"])
        with allure.step("Check host state has changed"):
            assert (
                cluster_host_page.get_host_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success host job"):
            assert (
                cluster_host_page.header.get_success_job_amount_from_header() == "1"
            ), "There should be 1 success host job in header"

    def test_check_delete_host_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        cluster, _ = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        with cluster_host_page.table.wait_rows_change():
            cluster_host_page.delete_host_by_row(row)
        with allure.step("Check there are no rows"):
            assert len(cluster_host_page.table.get_all_rows()) == 0, "Host table should be empty"

    def test_delete_linked_host_from_cluster_components_page(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        params = {"message": "[ CONFLICT ] HOST_CONFLICT -- Host #1 has component(s)"}
        cluster, host = create_community_cluster_with_host_and_service
        cluster.hostcomponent_set((host, cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)))
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.delete_host_by_row(row)
        with allure.step("Check error message"):
            assert cluster_host_page.get_info_popup_text() == params["message"], "No error message"

    def test_open_host_config_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        cluster, host = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_config_btn_in_row(row)
        HostConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, host.id).wait_page_is_opened()

    def test_check_pagination_on_cluster_host_page(self, app_fs, upload_and_create_provider, create_community_cluster):
        cluster = create_community_cluster
        provider = upload_and_create_provider
        host_count = 11
        with allure.step(f'Create {host_count} hosts'):
            for i in range(host_count):
                host = provider.host_create(f"{HOST_NAME}_{i}")
                cluster.host_add(host)
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, 1).open()
        cluster_host_page.table.check_pagination(1)


class TestClusterComponentsPage:
    @pytest.mark.smoke()
    def test_check_cluster_components_page_open_by_tab(self, app_fs, create_community_cluster):
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_config_page.open_components_tab()
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_components_page.wait_page_is_opened()
        cluster_components_page.check_all_elements()

    def test_check_cluster_components_page_open_service_page(self, app_fs, create_community_cluster):
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        cluster_components_page.click_service_page_link()
        ClusterServicesPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    def test_check_cluster_components_page_open_hosts_page(self, app_fs, create_community_cluster):
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        cluster_components_page.click_hosts_page_link()
        ClusterHostPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    @pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, "provider")], indirect=True)
    def test_check_cluster_components_page_create_host(self, app_fs, bundle_archive, create_community_cluster):
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        cluster_components_page.click_add_host_btn()
        cluster_components_page.host_popup.create_provider_and_host(bundle_path=bundle_archive, fqdn=HOST_NAME)
        host_row = cluster_components_page.get_host_rows()[0]
        check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")

    @pytest.mark.smoke()
    def test_check_cluster_components_page_create_components(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        params = {"message": "Successfully saved."}
        cluster, _ = create_community_cluster_with_host_and_service
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)
        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)

        cluster_components_page.close_info_popup()
        cluster_components_page.click_save_btn()
        with allure.step("Check that host and component are linked"):
            assert cluster_components_page.get_info_popup_text() == params["message"], "No message about success"
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "1")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(component_row), COMPONENT_NAME, "1")

    def test_check_cluster_components_page_restore_components(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        cluster, _ = create_community_cluster_with_host_and_service
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)
        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)

        cluster_components_page.close_info_popup()
        cluster_components_page.click_restore_btn()
        with allure.step("Check that host and component are not linked"):
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(component_row), COMPONENT_NAME, "0")

    def test_check_cluster_components_page_delete_host_from_component(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        cluster, _ = create_community_cluster_with_host_and_service
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)

        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)
        cluster_components_page.click_save_btn()

        cluster_components_page.click_number_in_component(component_row)
        cluster_components_page.delete_related_item_in_row_by_name(component_row, HOST_NAME)

        with allure.step("Check that host and component are not linked"):
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(component_row), COMPONENT_NAME, "0")

    def test_add_few_hosts_to_component_on_cluster_components_page(self, sdk_client_fs, app_fs, create_host):
        with allure.step("Create cluster with service and host"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_SERVICES)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            cluster.service_add(name=f"{SERVICE_NAME}_1")
            cluster.host_add(create_host)

        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)

        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)
        with allure.step("Check that save button is disabled when not all required amount of hosts are linked"):
            assert cluster_components_page.check_that_save_btn_disabled(), "Save button should be disabled"


class TestClusterConfigPage:
    def test_cluster_config_page_open_by_tab(self, app_fs, create_community_cluster):
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.open_config_tab()
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, 1)
        cluster_config_page.wait_page_is_opened()
        cluster_config_page.check_all_elements()

    def test_filter_config_on_cluster_config_page(self, app_fs, create_community_cluster):
        params = {"search_param": "str_param", "group_name": "core-site"}
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        with cluster_config_page.config.wait_rows_change():
            cluster_config_page.config.search(params["search_param"])
        with allure.step(f"Check that rows are filtered by {params['search_param']}"):
            config_rows = cluster_config_page.config.get_all_config_rows()
            assert len(config_rows) == 1, "Rows are not filtered: there should be 1 row"
            assert (
                cluster_config_page.config.get_config_row_info(config_rows[0]).name == f"{params['search_param']}:"
            ), f"Name should be {params['search_param']}"
        with cluster_config_page.config.wait_rows_change():
            cluster_config_page.config.clear_search_input()
        with allure.step("Check that rows are not filtered"):
            config_rows = cluster_config_page.config.get_all_config_rows()
            assert len(config_rows) == 4, "Rows are filtered: there should be 4 row"
        with cluster_config_page.config.wait_rows_change(expected_rows_amount=2):
            cluster_config_page.config.click_on_group(params["group_name"])

    def test_save_custom_config_on_cluster_config_page(self, app_fs, create_community_cluster):
        params = {
            "row_value_new": "test",
            "row_value_old": "123",
            "config_name_new": "test_name",
            "config_name_old": "init",
        }
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.type_in_config_field(row=config_row, value=params["row_value_new"], clear=True)

        cluster_config_page.config.set_description(params["config_name_new"])
        cluster_config_page.config.save_config()
        cluster_config_page.config.compare_versions(params["config_name_old"])
        with allure.step("Check row history"):
            row_with_history = cluster_config_page.config.get_all_config_rows()[0]
            cluster_config_page.config.wait_history_row_with_value(row_with_history, params["row_value_old"])

    def test_reset_config_in_row_on_cluster_config_page(self, app_fs, create_community_cluster):
        params = {"row_name": "str_param", "row_value_new": "test", "row_value_old": "123", "config_name": "test_name"}
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.type_in_config_field(row=config_row, value=params["row_value_new"], clear=True)
        cluster_config_page.config.set_description(params["config_name"])
        cluster_config_page.config.save_config()

        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.reset_to_default(row=config_row)
        cluster_config_page.config.assert_input_value_is(
            expected_value=params["row_value_old"], display_name=params["row_name"]
        )

    def test_field_validation_on_cluster_config_page(self, app_fs, sdk_client_fs):
        params = {
            'pass_name': 'Important password',
            'req_name': 'Required item',
            'not_req_name': 'Just item',
            'wrong_value': 'test',
        }
        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_REQUIRED_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_config_page.config.check_password_confirm_required(params['pass_name'])
        cluster_config_page.config.check_field_is_required(params['req_name'])
        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.type_in_config_field(params['wrong_value'], row=config_row)
        cluster_config_page.config.check_field_is_invalid(params['not_req_name'])


class TestClusterStatusPage:
    def test_open_by_tab_cluster_status_page(self, app_fs, create_community_cluster):
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.open_status_tab()
        cluster_status_page = ClusterStatusPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_status_page.wait_page_is_opened()
        cluster_status_page.check_all_elements()

    def test_filter_cluster_status_page(self, app_fs, create_community_cluster_with_host_and_service):
        cluster, host = create_community_cluster_with_host_and_service
        cluster.hostcomponent_set((host, cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)))
        cluster_status_page = ClusterStatusPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        group_rows = cluster_status_page.get_all_config_groups()
        with allure.step("Check that there is one group"):
            assert len(group_rows) == 1, "There should be 1 group"
        group_row = group_rows[0]
        cluster_status_page.click_collapse_all_btn()
        cluster_status_page.wait_group_opened(group_row)
        cluster_status_page.click_collapse_all_btn()
        cluster_status_page.wait_group_closed(group_row)
        cluster_status_page.config.click_on_group(title=SERVICE_NAME)
        with allure.step("Check group rows"):
            group_info = cluster_status_page.get_config_group_info(group_row)
            with allure.step("Check that there is one item in group"):
                assert len(group_info) == 1, "There should be one item in group"
            assert (
                group_info[0].service == COMPONENT_NAME
            ), f"Component name should be {COMPONENT_NAME} and not {group_info[0].service}"
            assert (
                group_info[0].hosts[0] == HOST_NAME
            ), f"Host name should be {HOST_NAME} and not {group_info[0].hosts[0]}"


class TestClusterImportPage:
    def test_open_by_tab_cluster_import_page(self, app_fs, create_community_cluster):
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.open_import_tab()
        cluster_status_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_status_page.wait_page_is_opened()
        cluster_status_page.check_all_elements()

    def test_check_cluster_import_from_cluster_import_page(self, app_fs, create_import_cluster_with_service):
        params = {"message": "Successfully saved"}
        cluster, _, _, _ = create_import_cluster_with_service
        import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        import_item = import_page.get_import_items()[0]
        with allure.step("Check import on import page"):
            assert import_page.get_import_item_info(import_item) == ImportItemInfo(
                'Pre-uploaded Dummy cluster to import', 'Pre-uploaded Dummy cluster to import 2.5'
            ), "Text in import item changed"
        import_page.close_info_popup()
        import_page.click_checkbox_in_import_item(import_item)
        import_page.click_save_btn()
        with allure.step("Check that import is saved"):
            assert import_page.get_info_popup_text() == params["message"], "No message about success"
            assert import_page.is_chxb_in_item_checked(import_item), "Checkbox with import should have been checked"


class TestClusterActionPage:
    def test_open_by_tab_cluster_action_page(self, app_fs, create_community_cluster):
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.open_actions_tab()
        cluster_action_page = ClusterActionPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        cluster_action_page.wait_page_is_opened()
        cluster_action_page.check_all_elements()

    def test_run_action_on_cluster_action_page(self, app_fs, create_community_cluster):
        cluster_action_page = ClusterActionPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_action = cluster_action_page.get_all_actions()[0]
        cluster_action_page.click_run_btn_in_action(cluster_action)
        cluster_action_page.check_empty_page()
        with allure.step("Check success cluster job"):
            assert (
                cluster_action_page.header.get_in_progress_job_amount_from_header() == "1"
            ), "There should be 1 in progress cluster job in header"
