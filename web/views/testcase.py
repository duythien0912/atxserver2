# coding: utf-8
#

from rethinkdb import r
from logzero import logger
import subprocess
import time
import uiautomator2 as u2

from ..database import db, time_now
from .base import AuthRequestHandler, AdminRequestHandler
from .device import D, AcquireError, ReleaseError
from ..tests.android_test import AndroidMockTest

class APITestExampleHandler(AuthRequestHandler):
    """ Run test example """

    async def get(self):
        """ get user current using devices """

        devices = await db.table_devices.all()
        if not devices:
            raise EnvironmentError("No devices")
        logger.info("Device count: %d", await db.table_devices.count())
        device = devices[0]
        udid = device['udid']
        try:
            await D(udid).acquire("a@anonymous.com", 600)
        except AcquireError as e:
            self.set_status(403)
            logger.info(str(e))

        data = await db.table("devices").get(udid).run()
        source = None
        priority = 0
        for s in data.get('sources', {}).values():
            if s['priority'] > priority:
                source = s
                priority = s['priority']
        data['source'] = source
        adb_remote_addr = source['remoteConnectAddress']
        subprocess.run(['adb', 'connect', adb_remote_addr])
        time.sleep(1)

        d = u2.connect_usb(adb_remote_addr)
        print(d.info)
        d.screen_on()
        d.shell("input keyevent HOME")
        d.swipe(0.1, 0.9, 0.9, 0.1)
        try:
            d.app_info("io.appium.android.apis")
        except:
            d.app_install('https://github.com/openatx/atxserver2/releases/download/v0.2.0/ApiDemos-debug.apk')

        d.app_start("io.appium.android.apis", stop=True)
        d(text="App").click() # same as d.xpath("App").click()
        logger.debug("Assert Alert button exists")
        assert d(text="Alarm").wait()

        # d.set_fastinput_ime(False)
        d.app_stop("io.appium.android.apis")
        time.sleep(1)
        d.screen_off()

        try:
            await D(udid).release("a@anonymous.com")
        except ReleaseError as e:
            self.set_status(403)
            logger.info(str(e))

        self.write_json({"success": True, "data": AndroidMockTest().android_test()})

