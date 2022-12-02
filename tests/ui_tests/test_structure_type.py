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

"""Test designed to check config save with different config params"""

import os

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Service
from adcm_pytest_plugin import utils
from tests.ui_tests.app.page.cluster.page import ClusterGroupConfigConfig
from tests.ui_tests.app.page.service.page import ServiceConfigPage
from tests.ui_tests.test_cluster_list_page import CLUSTER_NAME

CONFIG_DIR = "config_save"


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient) -> Cluster:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), CONFIG_DIR))
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestServiceConfigSave:
    """Tests to check cluster config save"""

    INVISIBLE_GROUPS = [
        "string",
        "structure",
    ]
    STRUCTURE_ROW_NAME = "structure"
    CONFIG_NAME_NEW = "test_name"
    CONFIG_NAME_OLD = "init"
    GROUP_NAME = "service-group"
    CONFIG_PARAM_AMOUNT = 2
    CONFIG_ADVANCED_PARAM_AMOUNT = 1
    CHANGE_STRUCTURE_CODE = 12
    CHANGE_STRUCTURE_COUNTRY = "test-country"

    @allure.step("Save config and check popup")
    def _save_config_and_refresh(self, config):
        config.config.save_config()
        assert not config.is_popup_presented_on_page(), "No popup should be shown after save"
        config.driver.refresh()

    def check_invisible_params(self, service: Service, parameters_amount: int) -> None:
        """Method to check invisible groups in config"""
        config = service.config()
        assert len(config) == parameters_amount, f"There are should be {parameters_amount} config parameters"
        for group in self.INVISIBLE_GROUPS:
            assert group in config, "Invisible group should be present in config object"

    def check_advanced_params(self, config_page):
        """Method to check advanced params in config"""
        assert (
            config_page.config.config_rows_amount() == self.CONFIG_ADVANCED_PARAM_AMOUNT
        ), "Advanced params should be present only when 'Advanced' is enabled"
        config_page.config.click_on_advanced()
        assert (
            config_page.config.config_rows_amount() == self.CONFIG_PARAM_AMOUNT
        ), "All params should be present when 'Advanced' is enabled"
        config_page.config.click_on_advanced()

    @staticmethod
    def _check_read_only_params(config_page):
        """Method to check read only state of params"""
        string_row = config_page.config.get_all_config_rows()[0]
        structure_row = config_page.config.get_all_config_rows()[1]
        assert config_page.config.is_element_read_only(string_row), "Config param must be read_only"
        assert not config_page.config.is_element_read_only(structure_row), "Config param must be writable"

    def test_config_save(self, app_fs, sdk_client_fs):
        """Test to check config save with default params"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_config_default")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create service group config"):
            service_group_config = service.group_config_create(self.GROUP_NAME)
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            self._save_config_and_refresh(cluster_group_config_page)
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_empty(self, app_fs, sdk_client_fs):
        """Test to check config save with empty params"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_config_empty")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.check_history_btn_disabled()

        with allure.step("Add params to empty config and save"):
            service_config_page.config.click_add_item_btn_in_row(self.STRUCTURE_ROW_NAME)
            service_config_page.config.type_in_field_with_few_inputs(
                self.STRUCTURE_ROW_NAME, [self.CHANGE_STRUCTURE_COUNTRY, self.CHANGE_STRUCTURE_CODE], clear=False
            )
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            service_config_page.config.save_config()  # Without sleep 1.2 here will be popup
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config"):
            service_config_page.config.save_config()  # Without sleep 1.2 here will be popup
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_save_required(self, app_fs, sdk_client_fs):
        """Test to check config can not be saved when required params is empty"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_config_required")

        with allure.step("Create service config and check save button"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            assert service_config_page.config.is_save_btn_disabled(), "Save button must be disabled"

    def test_config_save_invisible(self, app_fs, sdk_client_fs):
        """Test to check config save with ui option invisible"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_invisible")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()

        with allure.step("Check config ui option invisible"):
            self.check_invisible_params(service, self.CONFIG_PARAM_AMOUNT)
            self._save_config_and_refresh(service_config_page)
            self.check_invisible_params(service, self.CONFIG_PARAM_AMOUNT)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

        with allure.step("Check cluster group config after save"):
            cluster_group_config_page.driver.refresh()
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_save_advanced(self, app_fs, sdk_client_fs):
        """Test to check config save with ui option advanced"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_advanced")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()

        with allure.step("Check config ui option advanced"):
            self.check_advanced_params(service_config_page)
            self._save_config_and_refresh(service_config_page)
            self.check_advanced_params(service_config_page)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

        with allure.step("Check cluster group config after save"):
            cluster_group_config_page.driver.refresh()
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_save_read_only(self, app_fs, sdk_client_fs):
        """Test to check config save with ui option advanced"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_read_only")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()

        with allure.step("Check config read_only options and save"):
            self._check_read_only_params(service_config_page)
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)

        with allure.step("Check config read_only options after save"):
            self._check_read_only_params(service_config_page)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

        with allure.step("Check cluster group config after save"):
            cluster_group_config_page.driver.refresh()
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_save_schema_dict(self, app_fs, sdk_client_fs):
        """Test to check config save"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)

        service = cluster.service_add(name="service_config_schema_dict")
        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            self._save_config_and_refresh(cluster_group_config_page)
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.GROUP_NAME)

    def test_config_group(self, app_fs, sdk_client_fs):
        """Test to check config save"""
        with allure.step("Create cluster and service"):
            cluster = cluster_bundle(sdk_client_fs)
            service = cluster.service_add(name="service_config_default")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()

        with allure.step("Change structure params in group config and disable customization checkbox"):
            structure_row = cluster_group_config_page.group_config.get_all_group_config_rows()[1]
            cluster_group_config_page.group_config.click_on_customization_chbx(structure_row)
            cluster_group_config_page.group_config.type_in_field_with_few_inputs(
                structure_row, [self.CHANGE_STRUCTURE_CODE], clear=True
            )
            cluster_group_config_page.group_config.click_on_customization_chbx(structure_row)

        with allure.step("Check popup message when saving"):
            service_config_page.config.save_config()
            assert service_config_page.is_popup_presented_on_page(), "Popup should be shown with try to save"
