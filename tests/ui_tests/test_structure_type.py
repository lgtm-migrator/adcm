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
from typing import Union

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, GroupConfig
from adcm_pytest_plugin import utils
from tests.functional.plugin_utils import AnyADCMObject
from tests.ui_tests.app.page.cluster.page import (
    ClusterConfigPage,
    ClusterGroupConfigConfig,
)
from tests.ui_tests.test_cluster_list_page import CLUSTER_NAME


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


def _get_config_and_attr(obj: Union[GroupConfig, AnyADCMObject]):
    full_conf = obj.config(full=True)
    return full_conf["config"], full_conf["attr"]


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_config_save(app_fs, sdk_client_fs):
    """Test to check config save"""
    params = {
        "config_name_new": "test_name",
        "config_name_old": "init",
        "group_name": "Test group",
    }
    with allure.step("Create cluster and service"):
        bundle = cluster_bundle(sdk_client_fs, "config_save")
        cluster = bundle.cluster_create(name=CLUSTER_NAME)

    with allure.step("Create cluster config"):
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_config_page.wait_page_is_opened()
        cluster_config_page.config.set_description(params["config_name_new"])

    with allure.step('Save cluster config and check that popup is not presented on page'):
        cluster_config_page.config.save_config()
        assert not cluster_config_page.is_popup_presented_on_page(), 'No popup should be shown after save'

    with allure.step('Check cluster config after save'):
        cluster_config_page.driver.refresh()
        cluster_config_page.config.compare_versions(params["config_name_old"])


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_group_config_save(app_fs, sdk_client_fs):
    """Test to check group config save"""
    params = {
        "config_name_new": "test_name",
        "config_name_old": "init",
        "group_name": "Test group",
    }
    with allure.step("Create cluster and service"):
        bundle = cluster_bundle(sdk_client_fs, "config_save")
        cluster = bundle.cluster_create(name=CLUSTER_NAME)

    with allure.step("Create group config"):
        cluster_group_config = cluster.group_config_create(name="Test group")
        cluster_group_config_page = ClusterGroupConfigConfig(
            app_fs.driver, app_fs.adcm.url, cluster.id, cluster_group_config.id
        ).open()
        cluster_group_config_page.wait_page_is_opened()
        cluster_group_config_page.config.set_description(params["config_name_new"])

    with allure.step("Save group config and check that popup is not presented on page"):
        cluster_group_config_page.config.save_config()
        assert not cluster_group_config_page.is_popup_presented_on_page(), 'No popup should be shown after save'

    with allure.step("Check cluster group config after save"):
        cluster_group_config_page.driver.refresh()
        cluster_group_config_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, params['group_name'])
