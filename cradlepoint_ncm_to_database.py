from multiprocessing.dummy import Pool
from utilities import utilities
from credentials import credentials as secrets
import cradlepoint_database_repository as cdr
import json
import uuid


file = open('project/databases/macs.json')
mac_address_list = []
file.close()
devices = {}


def process_macs(mac_address):
    session = utilities.create_ncm_session()

    device = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?'
                         f'mac={mac_address}&'
                         f'fields=serial_number,id')

    if 200 >= device.status_code < 300:
        device = device.json()['data'][0]
        devices.update({device['id']: {'serial_number': device['serial_number']}})

        net_devices = session.get(f'https://www.cradlepointecm.com/api/v2/net_devices/?'
                                  f'fields=type,name,hostname,iccid,imei,mac&'
                                  f'router={device["id"]}')
        if 200 >= net_devices.status_code < 300 and net_devices.json()['data']:
            net_devices = net_devices.json()['data']
            for net_device in net_devices:
                net_device_id = device['id']
                if net_device['type'] == 'mdm' and net_device['iccid']:
                    print(net_device['iccid'])
                    devices[net_device_id].update({'iccid': net_device['iccid'], 'imei': net_device['imei']})
                elif net_device['type'] == 'ethernet' and net_device['mac']:
                    devices[net_device_id].update({'mac': net_device['mac']})
                devices[net_device_id].update({'identifier': ''})
        else:
            print(f"Net device for: {device['serial_number']} is not available")
    else:
        print("Device not in NCM")


def run():
    if len(mac_address_list) == 0:
        print(f"No mac's provided")
        return

    pool = Pool(len(mac_address_list))
    for _ in pool.imap(process_macs, mac_address_list):
        pass

    for device in devices:
        if ['serial_number', 'mac', 'iccid', 'imei', 'identifier'] == list(devices[device]):
            database = cdr.Database()
            part = cdr.Part()
            part_status = cdr.PartStatus()
            part_tag_data = cdr.PartTagData()
            part.part_guid = uuid.uuid1()
            part.part_definition_key = ''
            part.part_definition_base_key = ''
            part.serial_number = devices[device]['serial_number']
            part.part_status_enum = '1' 
            part.status_update_user_id = secrets.software_guid
            part.status_update_date = cdr.date()

            query_serial = database.select_part_where_serial_number(devices[device]['serial_number'])
            new_serial = query_serial.empty
            if new_serial:
                print(f"Adding part to database")
                result = database.insert_part(part)
                part_key = result.to_dict('records')[0]['partKey']

                part_status.part_key = part_key
                part_status.start_date = cdr.date()
                part_status.part_status_enum = 1
                part_status.user_id = secrets.software_guid
            else:
                part.part_guid = query_serial['partGuid'].values[0]
            for tag in ['Modem SIM ICCID', 'Modem Ethernet MAC Address', 'Modem IMEI']:
                part_tag_data.part_guid = part.part_guid
                part_tag_data.part_tag_data_definition_name = tag

                if tag == 'Modem SIM ICCID':
                    part_tag_data.value = devices[device]['iccid']
                elif tag == 'Modem Ethernet MAC Address':
                    part_tag_data.value = devices[device]['mac']
                elif tag == 'Modem IMEI':
                    part_tag_data.value = devices[device]['imei']
                elif tag == 'Modem Identifier':
                    part_tag_data.value = devices[device]['identifier']
                part_tag_data.user_id = secrets.software_guid
                part_tag_data.tag_date = cdr.date()

                print(f"Adding {tag} tag to database")
                database.insert_part_tag_data(part_tag_data)
        else:
            print(f"Not all tags available: {devices[device]['serial_number']}\n")
            return

        print(f"Completed: {devices[device]['serial_number']}\n")


run()
