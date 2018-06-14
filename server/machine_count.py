import requests
import server

class TokenAuth:
    def __init__(self, api_token):
        self.token = api_token

    def __call__(self, request):
        request.headers['Authorization'] = self.token
        return request

def machine_count(api_token, machine_type):
    print(api_token)
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





    

