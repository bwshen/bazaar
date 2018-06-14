import yaml
import machine_count
from flask import Flask
from flask import request
from flask import jsonify
import sys

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

sys.path.append('../lab/bin')  # noqa
from bodega_order import get_order_times

@app.route("/order_times/<sid>")
def get_list_orders(sid):
  (order_time, target_time) = get_order_times(sid)
  return "{'order_time':"+str(order_time)+",'target_time':"+str(target_time)+"}"


  
