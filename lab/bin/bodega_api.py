#!/usr/bin/env python


from flask import Flask

from bodega_order import get_order_times

app = Flask(__name__)
@app.route("/abc")

def hello():
    return "Hello World 2!"

@app.route("/order_times/<sid>")
def get_list_orders(sid):
  (order_time, target_time) = get_order_times(sid)
  return "{'order_time':"+str(order_time)+",'target_time':"+str(target_time)+"}"


  
