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

"""Test designed to check config save"""

import os

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Service
from adcm_pytest_plugin import utils
from tests.ui_tests.app.page.cluster.page import ClusterGroupConfigConfig
from tests.ui_tests.app.page.service.page import ServiceConfigPage
from tests.ui_tests.test_cluster_list_page import CLUSTER_NAME

CONFIG_PARAMETERS_AMOUNT = 2
CONFIG_ADVANCED_PARAMETERS_AMOUNT = 1


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestServiceConfigSave:
    """Tests to check cluster config save"""

    INVISIBLE_GROUPS = [
        "string",
        "structure",
    ]
    PARAMS = {
        "config_name_new": "test_name",
        "config_name_old": "init",
        "config_name_test": "name_for_test_save",
        "group_name": "service-group",
        "config_parameters_amount": CONFIG_PARAMETERS_AMOUNT,
        "config_advanced_parameters_amount": CONFIG_ADVANCED_PARAMETERS_AMOUNT,
    }

    @allure.step("Save config and check popup")
    def _save_config_and_check(self, config):
        """Method to save config and check popup"""
        config.config.save_config()
        assert not config.is_popup_presented_on_page(), "No popup should be shown after save"
        config.driver.refresh()

    def check_invisible_params(self, service: Service, parameters_amount: int) -> None:
        """Method to check invisible groups in config"""
        config = service.config()
        assert len(config.keys()) == parameters_amount, f"There are should be {parameters_amount} config parameters"
        for group in self.INVISIBLE_GROUPS:
            assert group in config.keys(), "Invisible group should be present in config object"

    def check_advanced_params(self, config_page):
        """Method to check advanced params in config"""
        assert (
            len(config_page.config.get_all_config_rows()) == self.PARAMS["config_advanced_parameters_amount"]
        ), "Advanced params should be present only when 'Advanced' is enabled"
        config_page.config.click_on_advanced()
        assert (
            len(config_page.config.get_all_config_rows()) == self.PARAMS["config_parameters_amount"]
        ), "All params should be present when 'Advanced' is enabled"
        config_page.config.click_on_advanced()

    def test_config_save(self, app_fs, sdk_client_fs):
        """Test to check config save"""
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "config_save")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)

        for service_config_name in ("service_config_default", "service_config_empty"):
            service = cluster.service_add(name=service_config_name)

        with allure.step("Create cluster and service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()
            service_config_page.config.set_description(self.PARAMS["config_name_new"])
            self._save_config_and_check(service_config_page)
            service_config_page.config.compare_versions(self.PARAMS["config_name_old"])

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.PARAMS["config_name_new"])

        with allure.step("Save group config and check that popup is not presented on page"):
            self._save_config_and_check(cluster_group_config_page)
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.PARAMS["group_name"])

    def test_config_save_invisible(self, app_fs, sdk_client_fs):
        """Test to check config save with ui option invisible"""
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "config_save")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name="service_invisible")

        with allure.step("Create cluster and service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()

        with allure.step("Check config ui options"):
            self.check_invisible_params(service, self.PARAMS["config_parameters_amount"])
            self._save_config_and_check(service_config_page)
            self.check_invisible_params(service, self.PARAMS["config_parameters_amount"])

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.PARAMS["config_name_new"])

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

        with allure.step("Check cluster group config after save"):
            cluster_group_config_page.driver.refresh()
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.PARAMS["group_name"])

    def test_config_save_advanced(self, app_fs, sdk_client_fs):
        """Test to check config save with ui option advanced"""
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "config_save")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name="service_advanced")

        with allure.step("Create cluster and service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.wait_page_is_opened()

        with allure.step("Check config ui options"):
            self.check_advanced_params(service_config_page)
            self._save_config_and_check(service_config_page)
            self.check_advanced_params(service_config_page)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.wait_page_is_opened()
            cluster_group_config_page.config.set_description(self.PARAMS["config_name_new"])

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

        with allure.step("Check cluster group config after save"):
            cluster_group_config_page.driver.refresh()
            cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, self.PARAMS["group_name"])
