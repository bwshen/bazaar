import yaml
import machine_count
from flask import Flask
from flask import request
from flask import jsonify
app = Flask(__name__)

@app.route("/")
def hello():
        return "Hello World!"

@app.route("/machine_count/<machine_type>")
def count_machine(machine_type):
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), machine_type))


def url():
    try:
        with open('server_config.yml', 'r') as server_profile:
            server_info = yaml.safe_load(server_profile)
        url = server_info['url']
    except Exception:
        raise Exception("Cannot find server config file")

    return url
