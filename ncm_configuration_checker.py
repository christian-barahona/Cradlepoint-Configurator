from multiprocessing.dummy import Pool
from utilities import utilities as ut

mac_address_list = []
skip_mac_entry = False
succeeded_count = 0


def ncm_group_check(mac_address):
    global succeeded_count
    session = ut.create_ncm_session()
    try:
        router_data = session.get(f'https://www.cradlepointecm.com/api/v2/routers/?mac={mac_address}', timeout=5).json()['data'][0]

        if len(router_data) == 0:
            ut.log_message("Router not in NCM")
            return

        serial_number = router_data['serial_number']

        if router_data['group'] is None:
            ut.log_message(f"{serial_number} Router is in NCM, but not in a group")
        else:
            actual_firmware = router_data['actual_firmware']
            target_firmware = router_data['target_firmware']

            if target_firmware != actual_firmware:
                ut.log_message(f"{serial_number} Firmware is not updated!")
            else:
                ut.log_message(f"{serial_number} Updated Successfully!")
                succeeded_count += 1
    except Exception as exception:
        ut.log_message(f"NCM Configuration Checker error with {mac_address}: {exception}")


def run():
    global skip_mac_entry
    global succeeded_count
    while True:
        ut.clear_console()

        if not skip_mac_entry:
            while True:
                for mac in mac_address_list:
                    print(f"#{mac_address_list.index(mac) + 1} {mac}")

                if len(mac_address_list) > 0:
                    print('\r')

                mac_input = input('MAC Address: ')
                if mac_input == 'done' and len(mac_address_list) == 0:
                    return
                elif mac_input == 'done':
                    break

                valid_mac_address = ut.mac_address_filter(mac_input, 'validate')
                if valid_mac_address:
                    mac_address = ut.mac_address_filter(mac_input, 'mac')
                    if mac_address not in mac_address_list:
                        mac_address_list.append(mac_address)

                ut.clear_console()

            skip_mac_entry = True
            
            print('\r')

        pool = Pool(len(mac_address_list))
        for _ in pool.imap(ncm_group_check, mac_address_list):
            pass

        print('\r')

        print(f'{succeeded_count}/{len(mac_address_list)} completed \n')

        # succeeded_count = 0

        user_response = input('Press ENTER to recheck. \nType \'done\' to exit. \nType \'add\' to add more. \nType \'clear\' to clear list: ') if not skip_mac_entry else 'done'

        if user_response == 'done':
            break
        elif user_response == 'add':
            skip_mac_entry = False
        elif user_response == 'clear':
            mac_address_list.clear()
            skip_mac_entry = False


if __name__ == "__main__":
    run()
