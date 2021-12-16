import time
from multiprocessing.dummy import Pool
from utilities import utilities
import os
import ncm_configuration_checker
import cradlepoint_ncm_to_database

mac_address_list = []
affected_routers_list = []
group_id = ''


def process_macs(mac_address):
    session = utilities.create_ncm_session()
    target_group = f'https://www.cradlepointecm.com/api/v2/groups/{group_id}/'
    target_group_account = session.get(target_group, timeout=10).json()['account']
    target_group_data = '{"group": "' + target_group + '"}'

    try:
        router = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac={mac_address}', timeout=10)
        if 200 >= router.status_code < 300:
            router_id = router.json()['data'][0]['id']
            router = session.get(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/', timeout=10).json()
            if router['group'] == target_group:
                group_url = router['group']
                if group_url != 'null':
                    group_name = session.get(group_url, timeout=2).json()['name']
                    utilities.log_message(f"Router '{mac_address}' is already in group: {group_name} \n")
                else:
                    utilities.log_message(f"Router '{mac_address}' is already in group: {group_url} \n")
            else:
                router_account = router['account']
                if router_account != target_group_account:
                    target_group_account_name = session.get(target_group_account).json()['name']
                    target_account_data = '{"account": "' + target_group_account + '"}'
                    session.put(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/', data=target_account_data, timeout=2)
                    utilities.log_message(f"Moved router '{mac_address}' to: {target_group_account_name}")
                    print("\r")
                session.put(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/', data=target_group_data, timeout=2)
                router_group = session.get(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/', timeout=10).json()['group']
                router_group_name = session.get(router_group, timeout=2).json()['name']
                utilities.log_message(f"Router '{mac_address}' is assigned to group: {router_group_name} \n")
                affected_routers_list.append(mac_address)
        else:
            utilities.log_message(f"Router '{mac_address}' not in ECM \n")
    except Exception as exception:
        utilities.log_message(f"Exception for router '{mac_address}': {exception} \n")


def run():
    global group_id
    os.system('cls')

    while True:
        for mac in mac_address_list:
            print(f"#{mac_address_list.index(mac) + 1} {mac}")

        if len(mac_address_list) > 0:
            print('\r')

        if len(mac_address_list) == 0:
            mac_input = input('MAC Address: ')
            if mac_input == 'done':
                break

            valid_mac_address = utilities.mac_address_filter(mac_input, 'validate')
            if valid_mac_address:
                mac_address = utilities.mac_address_filter(mac_input, 'mac')
                if mac_address not in mac_address_list:
                    mac_address_list.append(mac_address)

            os.system('cls')

            print('\r')
        else:
            break

    pool = Pool(len(mac_address_list))
    for _ in pool.imap(process_macs, mac_address_list):
        pass

    utilities.log_message(f"Total routers affected: {len(affected_routers_list)}")
    print('\r')

run()

checker = ncm_configuration_checker
checker.skip_mac_entry = True
checker.mac_address_list.extend(mac_address_list)
while True:
    checker.run()
    if checker.succeeded_count == len(checker.mac_address_list):
        break
    time.sleep(30)

assigner = cradlepoint_ncm_to_database
assigner.mac_address_list.extend(mac_address_list)
assigner.run()
