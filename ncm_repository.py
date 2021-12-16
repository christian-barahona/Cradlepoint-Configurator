import threading
from utilities import utilities as utl
from queue import Queue

queue = Queue()
mac_list = []

class NetCloudManager:
    def __init__(self):
        self.session = utl.create_ncm_session()

    def get_router_id(self, mac):
        try:
            router_id = self.session.get(f'https://www.cradlepointecm.com/api/v2/routers/?'
                                         f'mac={mac}&'
                                         f'fields=id').json()['data'][0]['id']
            return router_id
        except TypeError as exception:
            print(exception)
            return False

    def remove_from_ncm(self, router_id):
        response = self.session.delete(f'https://www.cradlepointecm.com/api/v2/routers/{router_id}/').status_code

        if response == utl.no_content:
            return True

        return False


def process(mac):
    ncm = NetCloudManager()
    router_id = ncm.get_router_id(mac)

    if not router_id:
        return

    unregister_router = ncm.remove_from_ncm(router_id)

    if unregister_router:
        print(f"Successfully unregistered: {mac}, {utl.get_time('timestamp')}")
    else:
        print(f"Failed to unregister: {mac}, {utl.get_time('timestamp')}")


def queue_mac():
    while True:
        try:
            mac = queue.get()
            process(mac)
        except Exception as exception:
            print(exception)
        queue.task_done()


def thread_maker(target):
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()


def processor():
    for mac in mac_list:
        thread_maker(queue_mac)
        queue.put(mac)

    queue.join()


processor()
