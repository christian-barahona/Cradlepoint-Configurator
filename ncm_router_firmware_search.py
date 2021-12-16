from utilities import utilities as utl
import re


session = utl.create_ncm_session()
router_list = []
firmware_version = ""


def query_ncm(url):
    response = session.get(url)
    return response


def get_device_list():
    url = 'https://www.cradlepointecm.com/api/v2/configuration_managers/' \
          '?limit=50' \
          '&fields=router.serial_number,router.actual_firmware,router.id,router.state,router.group.name'

    while True:
        response = query_ncm(url)
        data = response.json()['data']
        meta = response.json()['meta']
        firmware_regex = r"\/(\d+)\/"   # Find: /000/

        for item in data:
            if item['router']['actual_firmware'] is not None:
                firmware_version = item['router']['actual_firmware']
                matches = re.search(firmware_regex, firmware_version)
                if matches:
                    firmware_version = int(matches.group(1))
                    if firmware_version < firmware_version:
                        router_list.append(item['router'])
        
        if meta['next'] is None:
            break
        else:
            url = meta['next']

    for router in router_list:
        print(f"Serial Number: {router['serial_number']}")
        print(f"Router Id: {router['id']}")
        print(f"Group: {router['group']['name']}")
        print(f"State: {router['state']}")
        print(f"NetCloud OS Version: {router['state']}")
        print('\r')

    print(f'NetCloud OS Upgrade Required')
    print(f'Router count: {len(router_list)}')


get_device_list()
