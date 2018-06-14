import datetime
import requests
import server
import threading

class TokenAuth:
    def __init__(self, api_token):
        self.token = api_token

    def __call__(self, request):
        request.headers['Authorization'] = self.token
        return request

cache_reload_time = 5
cache = {}
refreshing = {}

#Security issue
#And multiprocessing issue (ie may need locks)
def machine_count(api_token, machine_type):
    if not machine_type in cache:
        result = machine_count_fresh(api_token, machine_type)
        cache[machine_type] = {"Value": result, "Time": datetime.datetime.now()}
        return result
    elif (datetime.datetime.now() - cache[machine_type]['Time']).total_seconds() < cache_reload_time or machine_type in refreshing:
        return cache[machine_type]['Value']
    else:
        refreshing[machine_type] = 0
        thr = threading.Thread(target=refresh_machine, args=([api_token, machine_type])).start()
        return cache[machine_type]['Value']



def refresh_machine(api_token, machine_type):
    cache[machine_type] = {"Value": machine_count_fresh(api_token, machine_type), "Time": datetime.datetime.now()}
    del refreshing[machine_type]



def machine_count_fresh(api_token, machine_type):
    kwargs = {'auth': TokenAuth(api_token)}
    kwargs['verify'] = False

    endpoint = machine_type
    print("Worked")
    print(server.url().rstrip('/') + '/' + endpoint.lstrip('/'))
    response = requests.request('GET', server.url().rstrip('/') + '/' + endpoint.lstrip('/'), **kwargs)

    json = response.json()

    total_free = 0

    while True:
        for machine in json['results']:
            if machine['held_by'] is None:
                total_free += 1

        if not json['next'] is None:
            json = requests.request('GET', json['next'], **kwargs).json()
        else:
            break

    print(json)
    return {'free': total_free, 'machines': json['count']}

