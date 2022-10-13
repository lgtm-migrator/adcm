from typing import Generator

import allure
import pytest
from selenium.common.exceptions import WebDriverException

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.conftest import login_over_api


@pytest.fixture(scope="module")
def app_ms(adcm_ms, web_driver) -> ADCMTest:
    web_driver.attache_adcm(adcm_ms)
    # see app_fs for reasoning
    try:
        web_driver.new_tab()
    except WebDriverException:
        web_driver.create_driver()
    return web_driver


@allure.title("Login in ADCM over API")
@pytest.fixture(scope="module")
def login_over_api_ms(app_ms, adcm_credentials):
    login_over_api(app_ms, adcm_credentials).wait_config_loaded()


@pytest.fixture()
def objects_to_delete() -> Generator[list, None, None]:
    objects = []
    yield objects
    for obj in objects:
        obj.delete()
