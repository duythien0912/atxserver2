# coding: utf-8
#

import re
import subprocess
import time
from pprint import pprint

import requests
from logzero import logger

import uiautomator2 as u2

server_url = "http://localhost:4000"
token = "2abd5c5fda8c460d9bc6e18a3270ecca"  # change to your token


def make_url(path):
    if re.match(r"^https?://", path):
        return path
    return server_url + path


def request_api(path, method="GET", **kwargs):
    kwargs['headers'] = {"Authorization": "Bearer " + token}
    r = requests.request(method, make_url(path), **kwargs)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        pprint(r.text)
        raise
    return r.json()


def main():
    logger.debug("Run android_test.py")

    # Get user information
    ret = request_api("/api/v1/user")
    logger.info("User: %s", ret['username'])

    # Get a list of available devices
    ret = request_api("/api/v1/devices", params={"usable": "true"})
    if not ret['devices']:
        raise EnvironmentError("No devices")
    logger.info("Device count: %d", ret['count'])

    # Occupy equipment
    device = ret['devices'][0]
    udid = device['udid']
    logger.info("Choose device: \"%s\" udid=%s", device['properties']['name'],
                udid)
    ret = request_api("/api/v1/user/devices",
                      method="post",
                      json={"udid": udid})
    print(ret)

    try:
        # Get information about occupied equipment
        ret = request_api("/api/v1/user/devices/" + udid)
        source = ret['device']['source']
        pprint(source)

        # Install the app
        logger.info("install app")
        provider_url = source['url']
        ret = request_api(
            provider_url + "/app/install",
            method="post",
            params={"udid": udid},
            data={
                "url":
                "https://github.com/openatx/atxserver2/releases/download/v0.2.0/ApiDemos-debug.apk"
            })
        pprint(ret)

        # Run test
        adb_remote_addr = source['remoteConnectAddress']
        subprocess.run(['adb', 'connect', adb_remote_addr])
        time.sleep(1)
        d = u2.connect_usb(adb_remote_addr)
        print(d.info)
        d.app_start("io.appium.android.apis")
        d.xpath("App").click()  # same as d(text="App").click()
        logger.debug("Assert Alert button exists")
        assert d(text="Alarm").wait()

    finally:
        # Release device
        ret = request_api("/api/v1/user/devices/" + udid, method="delete")
        print(ret)


if __name__ == "__main__":
    main()
