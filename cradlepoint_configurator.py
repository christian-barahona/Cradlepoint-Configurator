import re
import time
import requests
import uuid
import json
import ncm_configuration_checker
import cradlepoint_database_repository as cdr
from getmac import get_mac_address
from credentials import credentials as secrets
from utilities import utilities as utl


class CradlepointConfigurator:
    def __init__(self):
        self.router_ip_address = None
        self.router_lan_mac_address = None
        self.router_password = None
        self.router_wlan_mac_address = None
        self.router_serial_number = None
        self.router_model = None
        self.router_firmware_version = None
        self.router_imei = None
        self.router_iccid = None
        self.skip_setting = False
        self.ssh = None

    def ssid_configuration(self, setting):
        if self.skip_setting:
            utl.log_message("SSID Config Skipped")
            return True
        utl.log_message("[Removing all SSID's]") if setting == 'remove' else utl.log_message("[Adding SSID]")
        if setting == 'add':
            self.ssh.command(f'set /config/wwan/radio/0/profiles/0 {secrets.SSID_CREDENTIALS}')
            ssid = self.ssh.command(f'get /config/wwan/radio/0/profiles/0/ssid')
            utl.log_message(f"SSID '{ssid}' added!")
            return True

        elif setting == 'remove':
            profiles = self.ssh.command(f'get /config/wwan/radio/0/profiles')
            if profiles == '[]':
                utl.log_message("SSID list is empty")
            while profiles != '[]':
                ssid = self.ssh.command(f'get /config/wwan/radio/0/profiles/0/ssid')
                self.ssh.command(f'delete /config/wwan/radio/0/profiles/0')
                profiles = self.ssh.command(f'get /config/wwan/radio/0/profiles')
                utl.log_message(f"SSID '{ssid}' was removed")
            return True

    def wwan_configuration(self, setting):
        if self.skip_setting:
            utl.log_message("WWAN Config Skipped")
            return True
        utl.log_message("[Enabling WWAN]") if setting == 'wwan' else utl.log_message("[Disabling WWAN]")
        state = self.ssh.command(f'set /config/wwan/radio/0/mode "{setting}" | get /config/wwan/radio/0/mode')
        if state == setting:
            utl.log_message("WWAN enabled!") if setting == 'wwan' else utl.log_message("WWAN disabled!")
            return True
        else:
            utl.log_message(f"Failed to set '{setting}' WWAN configuration")
            return False

    def connectivity_check(self, check_type):
        utl.log_message(f"[Checking router for internet connectivity]")
        time_start = utl.get_time('timestamp')
        timestamp = utl.get_time('time')
        while True:
            print("\r" + f"{timestamp} Checking {check_type} status: {utl.elapsed_time(time_start)}", end="")
            response = self.ssh.command(f'ping -c 2 google.com')
            offline_regex = r"\bunknown\shost"
            offline = re.search(offline_regex, response)
            status = None
            if not offline:
                status = 'online'
            elif offline:
                status = 'offline'
            if status == check_type:
                print("\n" + f"{utl.get_time('time')} Router is {check_type}!")
                return True
            time.sleep(1)

    def router_registration(self, registration_type):
        if registration_type == 'unregister':
            utl.log_message("[Unregistering router from NCM]")
        elif registration_type == 'register':
            utl.log_message("[Registering router to NCM]")

        time_start = utl.get_time('timestamp')
        timestamp = utl.get_time('time')
        count = 0

        if registration_type == 'unregister':
            self.ssh.command(f'set /control/ecm/unregister {int(time.time())}')
        elif registration_type == 'register':
            self.ssh.command(f'set /control/ecm/register {secrets.NCM_CREDENTIALS}')

        while True:
            print("\r" + f"{timestamp} Checking registration status: {utl.elapsed_time(time_start)}", end="")
            count += 1
            if count == 12:
                if registration_type == 'unregister':
                    self.ssh.command(f'set /control/ecm/unregister {int(time.time())}')
                    count = 0
                elif registration_type == 'register':
                    self.ssh.command(f'set /control/ecm/register {secrets.NCM_CREDENTIALS}')
                    count = 0
            ncm_state = self.ssh.command(f'get status/ecm/state').replace('"', '')
            if registration_type == 'unregister' and ncm_state == 'unmanaged':
                print("\n" + f"{utl.get_time('time')} Successfully unregistered router")
                return True
            elif registration_type == 'register' and ncm_state == 'connected':
                print("\n" + f"{utl.get_time('time')} Successfully registered router")
                return True
            time.sleep(5)

    def ncm_group_assignment(self, ncm_group_id):
        if ncm_group_id:
            ncm_group_id = ""
        utl.log_message("[Assigning to ECM group]")
        ecm_group = f"https://www.cradlepointecm.com/api/v2/groups/{ncm_group_id}/"

        session = utl.create_ncm_session()
        try:
            router_ecm_id = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac='
                                        f'{self.router_wlan_mac_address}', timeout=5).json()['data'][0]['id']

            data = {"group": ecm_group}
            session.put(f'https://www.cradlepointecm.com/api/v2/routers/{router_ecm_id}/', json=data, timeout=5)

            utl.log_message("Assigned!")
            return True
        except Exception as exception:
            utl.log_message(f"Failed to assign ECM group to router: {exception}")
            return False

    @staticmethod
    def ncm_clear_local_configuration():
        utl.log_message("[Clearing local configuration]")

    def get_modem_id(self):
        modem_ids = []
        device = 0
        while True:
            modem_id = self.ssh.command(f'get /state/wan/devices/{device}/id')
            if modem_id == 'null':
                break
            modem_ids.append(modem_id)
            device += 1
        return modem_ids

    def model_check(self):
        model = self.ssh.command(f'get /status/product_info/product_name')
        return model

    def remove_from_ncm_group(self):
        utl.log_message(f"[Removing router from NCM group]")
        session = utl.create_ncm_session()
        data = '{"group": null}'

        try:
            router = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac='
                                 f'{self.router_wlan_mac_address}', timeout=2)
            if 200 >= router.status_code < 300:
                if router.json()['data'][0]['group'] is not None:
                    router_id = router.json()['data'][0]['id']
                    session.put(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/', data=data, timeout=2)
                    router = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac='
                                         f'{self.router_wlan_mac_address}', timeout=2)
                    get_ecm_group = router.json()['data'][0]['group']
                    print(f"Router group cleared. Group: {get_ecm_group} \n")
                else:
                    print("Router group already cleared \n")
            else:
                print(f"Router not in NCM")
        except Exception as exception:
            print(f"Exception: {exception}")

    def disable_show_cloud_setup(self):
        self.ssh.command(f'set config/system/show_cloud_setup false')
        response = self.ssh.command(f'get config/system/show_cloud_setup')
        utl.log_message(f'Show Cloud Setup: {response.upper()}')
        return True

    def set_wifi_radio(self, setting):
        self.ssh.command(f"set config/wlan/radio/0/enabled {setting}")
        response = self.ssh.command(f"get config/wlan/radio/0/enabled")
        utl.log_message(f"WIFI Radio Enabled: {response}")

    def reboot_router(self):
        self.ssh.command("reboot")

    def add_to_database(self):
        part = cdr.Part()
        part_status = cdr.PartStatus()
        part_tag_data = cdr.PartTagData()

        database = cdr.Database()

        part.part_guid = uuid.uuid1()
        part.part_definition_key = ''
        part.part_definition_base_key = ''
        part.serial_number = self.router_serial_number
        part.part_status_enum = '1'
        part.status_update_user_id = secrets.software_guid
        part.status_update_date = cdr.date()

        utl.log_message(f"Adding part to database")
        result = database.insert_part(part)
        part_key = result.to_dict('records')[0]['partKey']

        part_status.part_key = part_key
        part_status.start_date = cdr.date()
        part_status.part_status_enum = 1
        part_status.user_id = secrets.software_guid

        utl.log_message(f"Adding part status to database")
        database.insert_part_status_log(part_status)

        for tag in ['Modem SIM ICCID', 'Modem Ethernet MAC Address', 'Modem IMEI']:
            part_tag_data.part_guid = part.part_guid
            part_tag_data.part_tag_data_definition_name = tag

            if tag == 'Modem SIM ICCID':
                part_tag_data.value = self.router_iccid
            elif tag == 'Modem Ethernet MAC Address':
                part_tag_data.value = self.router_wlan_mac_address
            elif tag == 'Modem IMEI':
                part_tag_data.value = self.router_imei

            part_tag_data.user_id = secrets.software_guid
            part_tag_data.tag_date = cdr.date()

            utl.log_message(f"Adding {tag} tag to database")
            database.insert_part_tag_data(part_tag_data)

        return True

    def get_device_details(self):
        modem_ids_query = self.ssh.command('get status/wan/devices')
        modem_ids_regex = r"mdm-[a-zA-Z0-9]*"
        modem_ids = re.findall(modem_ids_regex, modem_ids_query)
        active_modem = None
        sim_card_detected = True

        for modem_id in modem_ids:
            sim_status = self.ssh.command(f'get status/wan/devices/{modem_id}/status/error_text')
            if sim_status == 'null':
                active_modem = modem_id
                break

        if not active_modem:
            utl.log_message(f"ICCID could not be determined.")
            sim_card_detected = False

            if modem_ids:
                active_modem = modem_ids[0]
            else:
                utl.log_message(f"IMEI could not be determined.")
                return

        device_details = json.loads(self.ssh.command(f'get status/wan/devices/{active_modem}/diagnostics'))

        if sim_card_detected:
            self.router_iccid = device_details['ICCID']

        self.router_imei = device_details['DISP_IMEI']

    def configure(self, ncm_group_id=None):
        utl.log_message("[Starting configuration]")

        configured = \
            self.add_to_database() and \
            self.disable_show_cloud_setup() and \
            self.wwan_configuration('wwan') and \
            self.ssid_configuration('remove') and \
            self.ssid_configuration('add') and \
            self.connectivity_check("online") and \
            self.router_registration('unregister') and \
            self.router_registration('register') and \
            self.ncm_group_assignment(ncm_group_id)

        if configured:
            utl.log_message("Preliminary router configuration complete \n")
        else:
            utl.log_message("Router was not fully configured")

    def password_setter(self):
        scanned_serial_number = None
        while True:
            session = utl.http_session()
            mac_password = utl.mac_address_filter(self.router_lan_mac_address, 'password')
            secrets.CRADLEPOINT_PASSWORD_LIST.insert(0, mac_password)
            password_list = secrets.CRADLEPOINT_PASSWORD_LIST
            passwords = password_list if scanned_serial_number is None else [scanned_serial_number]

            for password in passwords:
                try:
                    session.auth = ('admin', password)
                    success = session.get(f"http://{self.router_ip_address}/api/success", timeout=2).json()['success']
                    if success:
                        self.router_password = password
                        return True
                    elif not success:
                        session = utl.http_session(username='admin', password=password, auth='digest')
                        success = session.get(f"http://{self.router_ip_address}/api/success",
                                              timeout=2).json()['success']
                        if success:
                            self.router_password = password
                            return True
                        elif not success and scanned_serial_number is not None:
                            return False
                except Exception as exception:
                    utl.log_message(f"Exception thrown while checking password: {exception}")
                    return False
            scanned_serial_number = input('Scan serial number: ')

    def remove_from_ncm(self):
        ncm_session = utl.create_ncm_session()
        try:
            ncm_id = self.get_ncm_id()
            if ncm_id is not False:
                ncm_session.delete(f'https://www.cradlepointecm.com/api/v2/routers/{ncm_id}/', timeout=5)
                time.sleep(2)
                self.get_ncm_id()
        except requests.RequestException as exception:
            utl.log_message(f'Failed to remove router from NCM: {exception}')

    def reset_to_factory(self):
        utl.log_message(f"[Resetting router to factory settings]")
        self.ssh.command(f'set /control/system/factory_reset 0')
        utl.log_message(f'Router reset to factory settings')

    def get_ncm_id(self):
        utl.log_message(f"[Getting NCM ID]")
        ncm_session = utl.create_ncm_session()
        try:
            router_data = ncm_session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac='
                                          f'{self.router_wlan_mac_address}', timeout=5)

            if router_data.status_code != utl.ok_status:
                utl.log_message("Incorrect MAC address used")
                return False
            elif len(router_data.json()['data']) == 0:
                utl.log_message("Router not in NCM")
                return False
            else:
                utl.log_message("Router is in NCM")
                ncm_id = router_data.json()['data'][0]['id']
                return ncm_id
        except requests.RequestException as exception:
            utl.log_message(f"NCM ID check exception: {exception}")

    def router_connection_check(self):
        ip_list = ['192.168.0.1', '192.168.3.1']
        connected = False
        session = utl.http_session()

        for ip in ip_list:
            try:
                ip_status_code = session.get(f'http://{ip}/', timeout=.5).status_code
                if ip_status_code == utl.ok_status:
                    connected = True
                    self.router_ip_address = ip
                    self.router_lan_mac_address = utl.mac_address_filter(get_mac_address(ip=ip), 'mac')
                    correct_password = True
                    self.router_password = input('Scan serial number: ')

                    if correct_password:
                        self.ssh = utl.SshClient(self.router_ip_address, 'admin', self.router_password)
                        self.get_device_details()
                        self.router_wlan_mac_address = self.ssh.command(f'get /status/product_info/mac0').replace('"', '').upper()
                        self.router_serial_number = self.ssh.command(f'get /status/product_info/manufacturing/serial_num').replace('"', '')
                        self.router_model = self.ssh.command(f'get /status/product_info/product_name').replace('"', '')
                        major_version = self.ssh.command(f'get /status/fw_info/major_version')
                        minor_version = self.ssh.command(f'get /status/fw_info/minor_version')
                        patch_version = self.ssh.command(f'get /status/fw_info/patch_version')
                        self.router_firmware_version = f'{major_version}.{minor_version}.{patch_version}'
                    elif not correct_password:
                        utl.log_message("Bad password used to log into router")
                        connected = False
                    break
            except requests.RequestException:
                pass
        return connected

    def mode_selector(self):
        skip = ""
        group = ""

        while True:
            utl.clear_console()
            connected = self.router_connection_check()
            if not connected:
                response = input("Router not connected. Press ENTER to retry or type 'done' to exit: ")
                print("\n")
                if response == "done":
                    quit()
                else:
                    continue

            self.disable_show_cloud_setup()

            utl.log_message(f"Model: {self.router_model}")
            utl.log_message(f"Serial number: {self.router_serial_number}")
            utl.log_message(f"Router password: {self.router_password}")
            utl.log_message(f"Router IP: {self.router_ip_address}")
            utl.log_message(f"SIM Card Number: {self.router_iccid}")
            utl.log_message(f"Router IMEI: {self.router_imei}")
            utl.log_message(f"Router MAC: {self.router_wlan_mac_address}")
            utl.log_message(f"Router Firmware Version: {self.router_firmware_version}")
            utl.log_message(f"WWAN State: {self.ssh.command(f'get /config/wwan/radio/0/mode')}")
            utl.log_message(f"SSID State: {self.ssh.command(f'get /config/wwan/radio/0/profiles/0/ssid')}")

            previous_mode = False
            ncm_configuration_checker.ncm_group_check(self.router_wlan_mac_address)
            mode = input("\n" + "Type r to repeat previous configuration \n"
                                "Type 1 to run device Configurator \n"
                                "Type 2 to register device to NCM \n"
                                "Type 3 to enable WIFI radio, enable WWAN, and to set temporary SSID for config \n"
                                "Type 4 to clear SSID and disable WWAN \n"
                                "Type 5 to disable \"Show Cloud Setup\" \n"
                                "Type 6 to reboot device \n"
                                "Type 7 to factory reset device \n\n"
                                "Type \"done\" to exit \n\n"
                                "Mode: ")
            print("\n")
            if mode == "1" or mode == "r":
                if mode == "r":
                    previous_mode = True

                while True:
                    skip = input('Skip temp WIFI setup? \n Type "yes" or "no" or type "done" to exit: ') if not previous_mode else skip
                    if skip == 'yes':
                        self.skip_setting = True
                        break
                    elif skip == 'no':
                        break
                group = input("\n" + "Enter NCM group number: ") if not previous_mode else group
                self.configure(group)
                input("Press ENTER to continue \n")
            elif mode == "2":
                self.router_registration('register')
                input("Press ENTER to continue \n")
            elif mode == "3":
                self.set_wifi_radio('true')
                self.ssid_configuration('remove')
                self.ssid_configuration('add')
                self.wwan_configuration('wwan')
                self.connectivity_check('online')
                input("Press ENTER to continue \n")
            elif mode == "4":
                self.skip_setting = False
                self.ssid_configuration('remove')
                self.wwan_configuration('disabled')
                input("Press ENTER to continue \n")
            elif mode == "5":
                input("Press ENTER to continue \n")
            elif mode == "6":
                self.reboot_router()
            elif mode == "7":
                confirm = input("Are you sure you want to FACTORY RESET this device? \n Type 'yes' or 'no': ")
                if confirm == 'yes':
                    self.reset_to_factory()
                    self.remove_from_ncm()
                input("Press ENTER to continue \n")
            elif mode == "done":
                quit()


configurator = CradlepointConfigurator()
configurator.mode_selector()
