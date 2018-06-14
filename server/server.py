import yaml
import machine_count
from flask import Flask
from flask import request
from flask import jsonify
app = Flask(__name__)

@app.route("/")
def hello():
        return "Hello World!"

@app.route("/rktest_yml_count", methods=['GET'])
def rktest_yml_machine_count():
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), '/rktest_ymls'))

@app.route("/ubuntu_machines_count", methods=['GET'])
def ubuntu_machine_count():
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), '/ubuntu_machines/'))

@app.route("/esx_hosts_count", methods=['GET'])
def esx_hosts_count():
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), '/esx_hosts/'))

@app.route("/sd_dev_machines_count", methods=['GET'])
def sd_dev_machines_count():
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), '/sd_dev_machines/'))

@app.route("/mssql_servers_count", methods=['GET'])
def mssql_servers_count():
    return jsonify(machine_count.machine_count(request.headers.get('authorization'), '/mssql_servers/'))



def url():
    try:
        with open('server_config.yml', 'r') as server_profile:
            server_info = yaml.safe_load(server_profile)
        url = server_info['url']
    except Exception:
        raise Exception("Cannot find server config file")

    return url
