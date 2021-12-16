import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.tz import tz


class Report:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'X-CP-API-ID': None,
            'X-CP-API-KEY': None,
            'X-ECM-API-ID': None,
            'X-ECM-API-KEY': None,
            'Content-Type': 'application/json'
        })
        self.accounts = {}
        self.data = []

    def get_accounts(self):
        try:
            response = self.session.get('https://www.cradlepointecm.com/api/v2/accounts/')
            if response.status_code == 200:
                accounts = response.json()['data']
                for account in accounts:
                    record = {
                        account['resource_url']: {
                            "name": account['name'],
                            "id": account['id'],
                            "groups": {},
                            "router_count": 0
                        }
                    }
                    self.accounts.update(record)
        except requests.exceptions.RequestException as exception:
            print(exception)

    def get_groups(self):
        try:
            response = self.session.get('https://www.cradlepointecm.com/api/v2/groups/?'
                                        'limit=500&'
                                        'fields=name,account,resource_url,id')
            if response.status_code == 200:
                groups = response.json()['data']
                for group in groups:
                    record = {
                        group['resource_url']: {
                            "name": group['name'],
                            "id": group['id'],
                            "active_routers": [],
                            "inactive_routers": []
                        }
                    }
                    self.accounts[group['account']]['groups'].update(record)
        except requests.exceptions.RequestException as exception:
            print(exception)

    def get_routers(self):
        local_time_now = datetime.now().astimezone(tz.tzlocal())
        thirty_days_ago = local_time_now - timedelta(days=30)

        def sort_routers():
            record = {
                "No Group": {
                    "name": "No Group",
                    "id": None,
                    "active_routers": [],
                    "inactive_routers": []
                }
            }
            self.accounts[account]['groups'].update(record)
            for router in routers:
                self.accounts[account]['router_count'] += 1
                state_updated_at = router['state_updated_at']
                if state_updated_at is not None:
                    last_update_date = \
                        datetime.strptime(state_updated_at, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(
                            tz.tzlocal())
                else:
                    last_update_date = None

                account_name = self.accounts[account]['name']
                serial = router['serial_number']
                group_name = None
                active_state_flag = False
                state_updated_at = router['state_updated_at'] if not None else None

                if router['group'] is not None:
                    group_name = self.accounts[account]['groups'][router['group']]['name']

                if router['state'] == 'online' and last_update_date > thirty_days_ago:
                    if router['group'] is None:
                        active_state_flag = True

                self.data.append([account_name, serial, group_name, active_state_flag, state_updated_at])

        for account in self.accounts:
            routers = []
            url = f'https://www.cradlepointecm.com/api/v2/routers/?' \
                  f'account__in={self.accounts[account]["id"]}&' \
                  f'limit=500&' \
                  f'fields=state,state_updated_at,group,serial_number'
            while True:
                try:
                    response = self.session.get(url)
                    if response.status_code == 200:
                        routers.extend(response.json()['data'])
                        meta = response.json()['meta']
                        if meta['next'] is None:
                            break
                        else:
                            url = meta['next']
                except requests.exceptions.RequestException as exception:
                    print(exception)
                    break
            sort_routers()


report = Report()
report.get_accounts()
report.get_groups()
report.get_routers()

df = pd.DataFrame(report.data, columns=['accountName', 'serial', 'groupName', 'activeStateFlag', 'stateUpdatedAt'])
