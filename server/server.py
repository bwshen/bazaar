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
  return jsonify({'order_time': str(order_time), 'target_time': str(target_time)})

from bodega_order import get_monthly_cost
@app.route("/monthly_cost/<user_sid>")
def monthly_cost(user_sid):
  (cost0, cost1, cost2, cost3) = get_monthly_cost(user_sid)
  return "{'cost_1stmonth':"+str(cost0)+",cost_2ndmonth':"+str(cost1)+",'cost_3rdmonth':"+str(cost2)+",'cost_4thmonth':"+str(cost3)+"}"

  
if __name__ == '__main__':
 app.run(threaded=True)
