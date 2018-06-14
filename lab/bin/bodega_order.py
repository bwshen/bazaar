#!/usr/bin/env python

"""Reserve a pod through Bodega interface."""
import argparse
import json
import logging
import os
import sys
import time
import subprocess
import yaml
import collections
import requests

from datetime import timedelta
from urlparse import urlparse
from datetime import datetime
from operator import attrgetter

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # noqa
SCRIPT_NAME = os.path.basename(__file__)  # noqa
SDMAIN_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))  # noqa

DEBUG = '1'
FUDGE=0.2

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'bodega', 'client'))  # noqa
from bodega_client import BodegaClient

sys.path.append(os.path.join(SDMAIN_ROOT, 'lab', 'lib'))  # noqa
from logging_init import init_logging

# from pre_build import fetch_testbed_resource_yamls

log = logging.getLogger(os.path.basename(__name__))

# disable warning
requests.packages.urllib3.disable_warnings()

# Collection for carrying order attributes
hostT = collections.namedtuple('hostT',
                               'name owner platform restype days location '+
                               'ejection sid restime justification pool')
pools = {}

def list_resources(bodega_client):
    next = 'temp'
    page = 1
    itemc = 0
    hostlist=[]
    resources={}

    print ('time:'+time.strftime("%H:%M:%S"))
    print ('fetching orders ...')
    count=0
    pbar_size = 80
    pbar_grid = 1
    next_pbar_grid=pbar_grid

    # Looping through pages of orders
    while (next):
      order_page  = bodega_client.get('/rktest_ymls', 
                                      params={'page' : [page], 
                                              'status' : ['FULFILLED']})
      results = order_page['results']
      next = order_page['next']
      # Looping through orders of each page
      for item in results:
        name = item['name']
        platform = item['platform']
        location = item['location']
        host = hostT(name=name,restype='rktest.yml',platform=platform,
                     location=location, restime='',owner='',days='')
        if (platform+'-'+location) not in resources:
          hostlist=[host]
          resources[platform+'-'+location] = hostlist
        else:
          resources[platform+'-'+location].append(host)
      page+=1

    print('\n\n\n--------------------')

    return resources

def print_page_header(mode, title):
    if (mode=='TEXT'):
      print title
    else:
       print ("""<!DOCTYPE html><html><head resURL="http://master-builds.corp.rubrik.com/static/63f502da" data-rooturl="" data-resurl="http://master-builds.corp.rubrik.com/static/63f502da"><title>Bodea Orders</title><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/css/layout-common.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/css/style.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/css/color.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/css/responsive-grid.css" type="text/css" /><link rel="shortcut icon" href="http://master-builds.corp.rubrik.com/static/63f502da/favicon.ico" type="image/vnd.microsoft.icon" /><link color="black" rel="mask-icon" href="http://master-builds.corp.rubrik.com/images/mask-icon.svg" /><script>var isRunAsTest=false; var rootURL=""; var resURL="http://master-builds.corp.rubrik.com/static/63f502da";</script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/prototype.js" type="text/javascript"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/behavior.js" type="text/javascript"></script><script src="/adjuncts/63f502da/org/kohsuke/stapler/bind.js" type="text/javascript"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/yahoo/yahoo-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/dom/dom-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/event/event-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/animation/animation-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/dragdrop/dragdrop-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/container/container-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/connection/connection-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/datasource/datasource-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/autocomplete/autocomplete-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/menu/menu-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/element/element-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/button/button-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/storage/storage-min.js"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/hudson-behavior.js" type="text/javascript"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/scripts/sortable.js" type="text/javascript"></script><script>crumb.init("", "");</script><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/container/assets/container.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/assets/skins/sam/skin.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/container/assets/skins/sam/container.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/button/assets/skins/sam/button.css" type="text/css" /><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/static/63f502da/scripts/yui/menu/assets/skins/sam/menu.css" type="text/css" /><link rel="search" href="http://master-builds.corp.rubrik.com/opensearch.xml" type="application/opensearchdescription+xml" title="Jenkins" /><meta name="ROBOTS" content="INDEX,NOFOLLOW" /><script src="http://master-builds.corp.rubrik.com/adjuncts/63f502da/org/kohsuke/stapler/jquery/jquery.full.js" type="text/javascript"></script><script>var Q=jQuery.noConflict()</script><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/doony/2.1/css/doony.min.css" type="text/css" />""")

       print ("""<script src="https://cdnjs.cloudflare.com/ajax/libs/doony/2.1/js/doony.min.js" type="text/javascript"></script><script src="http://master-builds.corp.rubrik.com/static/63f502da/jsbundles/page-init.js" type="text/javascript"></script></head><body data-model-type="org.jenkins.plugins.lockableresources.actions.LockableResourcesRootAction" id="jenkins" class="yui-skin-sam jenkins-2.19.4 two-column" data-version="2.19.4"><a href="#skip2content" class="skiplink">Skip to content</a><div id="page-head"><div id="header"><div class="logo"><a id="jenkins-home-link" href="http://master-builds.corp.rubrik.com/"><img src="http://master-builds.corp.rubrik.com/static/63f502da/images/headshot.png" alt="title" id="jenkins-head-icon" /><img src="http://master-builds.corp.rubrik.com/static/63f502da/images/title.png" alt="title" width="139" id="jenkins-name-icon" height="34" /></a></div><div id="breadcrumbBar"><tr id="top-nav"><td id="left-top-nav" colspan="1"><link rel="stylesheet" href="http://master-builds.corp.rubrik.com/adjuncts/63f502da/lib/layout/breadcrumbs.css" type='text/css' /><script src="http://master-builds.corp.rubrik.com/adjuncts/63f502da/lib/layout/breadcrumbs.js" type="text/javascript"></script><div class="top-sticker noedge"><div class="top-sticker-inner"><div id="right-top-nav"><div id="right-top-nav"></div></div></div><div id="breadcrumb-menu-target"></div></div></div></td></tr></div></div><div id="page-body" class="clear"></div><div id="main-panel">""")

# <div id="side-panel">

def print_page_footer(mode, footer):
    if (mode=='TEXT'):
      print footer
    else:
      print '<br><br><br><br><br><br><b>'+footer+'<br></b></html>'

def print_table_header(mode, header,order_status):
    if (mode=='TEXT'):
      print header
    else:
      print '<br><br><b>'+header+'</b>'
      if (order_status=='FULFILLED'):
        print ("""<table class="pane" style="width: 80%;" border="thick solid"><tbody><tr><td width="10%" class="pane-header">item#</td><td width="15%" class="pane-header">order#</td><td width="5%" class="pane-header">Days Held</td><td width="5%" class="pane-header">Ejection</td><td width="25%" class="pane-header">Resource Name</td><td width="15%" class="pane-header">Type</td><td width="10%" class="pane-header">Held By</td><td width="20%" class="pane-header">Location</td>><td width="15%" class="pane-header">Justification</td></tr>""")
      elif (order_status=='OPEN'):
        print ("""<table class="pane" style="width: 80%;" border="thick solid"><tbody><tr><td width="10%" class="pane-header">item#</td><td width="15%" class="pane-header">order#</td><td width="5%" class="pane-header">Created</td><td width="5%" class="pane-header">Ejection</td><td width="15%" class="pane-header">Type</td><td width="10%" class="pane-header">Requested By</td><td width="20%" class="pane-header">Location</td></tr>""")

def print_line(mode, line):
    if (mode=='TEXT'):
      print(line)
    else:
      print('<br>'+line+'<br>')

def print_table_row(mode, order_status, itemcount, sid, days, name, 
                    platform, owner, location, restime, ejection, 
                    justification):
    if (mode=='TEXT'):
      print(str(itemcount)+' - sid:'+str(sid)+' days:'+days+' name:'+str(name)+
            ' platform:'+str(platform)+' ser:'+str(owner)+',location:'+
            str(location)+',created:'+str(restime)+', ejection:'+
            str(ejection))
      if len(justification)>0:
        print('Comment:'+str(justification))
    else:
      if (order_status=='FULFILLED'):
        if (owner=='Free'):
          owner='<b>Free</b>'
        if len(justification) > 0:
          justifyStr = 'For: <a href="'+str(justification)+'">'+ str(justification)+'</a>'
        else:
          justifyStr = '-'
        print('<tr><td>'+str(itemcount)+
              '</td><td><a href="https://bodega.rubrik-lab.com/api/orders/'+
              str(sid)+'/">'+str(sid)+'</a></td><td>'+days+'</td><td>'+
              str(ejection)+'</td><td><b>'+name+'</b></td><td>'+
              platform+'</td><td>'+str(owner)+'</td><td>'+str(location)+
              '</td><td>'+justifyStr+'</td></tr>')
      elif (order_status=='OPEN'):
        print('<tr><td>'+str(itemcount)+
              '</td><td><a href="http://bodega.rubrik-lab.com/api/orders/'+
              str(sid)+'/">'+str(sid)+'</a></td><td>'+str(restime)+
              '</td><td>'+platform+'</td><td>'+str(owner)+'</td><td>'+
              str(location)+'</td></tr>')

def print_table_footer(mode,footer):
    if (mode=='TEXT'):
      print footer
    else:
      print '</table>'
      print '<b>'+footer+'</b>'

def list_orders_int(bodega_client, order_status, display, platform):
    next = 'temp'
    page = 1
    itemc = 0

    hostlist=[]
    resources=[]

    print ('time:'+time.strftime("%H:%M:%S"))
    print ('fetching orders ...')
    count=0
    pbar_size = 80
    pbar_grid = 1
    next_pbar_grid=pbar_grid
    # serial number of orders
    sno = 0

    # Looping through pages of orders
    while (next):
      tried = 0
      try:
        order_page  = bodega_client.get('/orders',
                                        params={'page' : [page],
                                                'status' : [order_status]})
      except:
        print "Retrying fetch..."
        order_page  = bodega_client.get('/orders', 
                                        params={'page' : [page], 
                                                'status' : [order_status]})

      results = order_page['results']

      # Do initial set up
      if (page == 1):
        count = order_page['count'] * 1.1
        pbar_grid = count/pbar_size
        next_pbar_grid=pbar_grid
        print('pbar_grid:'+str(pbar_grid))
        # setup toolbar
        sys.stdout.write("[%s]" % ("*" * pbar_size))
        sys.stdout.flush()
        sys.stdout.write("\b" * (pbar_size+1)) 

      # Looping through orders of each page
      for item in results:
        fulfilled = item['fulfilled_items']
        sid = item['sid']
        owner = item['owner']
        held_by = owner['username']

        if (order_status == 'OPEN'):
          order_item = item['items']
          order_location = order_item.split('"location":')
          order_type = order_item.split('"type":')
          order_platform = order_item.split('"platform":')

          sno=sno+1
          time_created = item['time_created'].replace('T',' ').split('.')[0].replace('Z','')
          time_created_d = datetime.strptime(time_created,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)

          display_info=" - location:"
          if len(order_location)>1:
            order_location = order_item.split(
                '"location":')[1].split('"')[1].replace('_','')
            display_info+=order_location
          display_info+=" - type:"
          if len(order_type)>1:
            order_type = order_item.split('"type":')[1].split('"')[1]
            display_info+=order_type
          display_info+=" - platform:"
          if len(order_platform)>1:
            order_platform = order_item.split('"platform":')[1].split('"')[1]
            display_info+=order_platform

          display_info +=" - requester:"
          if len(held_by)>1:
            display_info+=held_by

          host = hostT(name='-',restime=time_created_d,restype=order_type,
                       owner=held_by, platform=order_platform, days='0', 
                       location=order_location, sid=sid, justification='-', 
                       ejection='', pool='')

        elif (order_status == 'FULFILLED'):
          itemjson = item['items_json']

          typeStr=''

          for ij in itemjson:
            typeStr+=itemjson[ij]['type']+' '

          # Loop for fulfilled items within each order
          for fitem in fulfilled:
            ft = fulfilled[fitem]
            held_time = ft['time_held_by_updated'].replace('T',' ').split('.')[0].replace('Z','')
            held_time_d = datetime.strptime(held_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)
            specific_url = ft['specific_item']
            platform=''
            location=''
            nameC=''
            if ('rktest_ymls' in specific_url):
              try:
                specific = bodega_client.get(specific_url.split('/api')[1])
                nameC = specific['name']
                if 'platform' in specific:
                  platform = specific['platform']
                else:
                  platform = 'TBD'
                if 'location' in specific:
                  location = specific['location']
                else:
                  location = 'TBD'
              except:
                nameC = "error in fetching "+specific_url.split('/api')
            td = datetime.now() - held_time_d
            tds = str(td.days)

            host = hostT(name=nameC,restime=held_tiime_d,restype=typeStr,
                         owner=held_by,platform=platform, days=tds, 
                         location=location, sid='-', justification='-', 
                         ejection='', pool='')

            resources.append(nameC)
          # End of fulfilled_item loop
        else:
          print('UNKNOWN STATUS CODE')
          return hostlist
        # End of if (order_status=)
        hostlist.append(host)

        itemc+=1

        if (itemc>next_pbar_grid):
          sys.stdout.write("-")
          sys.stdout.flush()
          next_pbar_grid+=pbar_grid

      # End of order loop
      next = order_page['next']
      page+=1
    # End of order page loop

    print('\n')
    print('=== total: '+str(itemc))

    sys.stdout.write("\b" * (pbar_size+1)) # return to start of line, after '['
    resources.sort()

    return hostlist

def list_items(bodega_client, display, platform):
    next = 'temp'
    page = 1
    itemc = 0

    hostlist=[]
    resources=[]


#    print ('fetching orders ...')
    count=0
    pbar_size = 80
    pbar_grid = 1
    next_pbar_grid=pbar_grid
    # serial number of orders
    sno = 1
    ejection_days = ''
    comment = ''

    # Looping through pages of orders
    while (next):
      order_page  = bodega_client.get('/rktest_ymls', 
                                      params={'page' : [page], 
                                              'platform' : [platform]})
      results = order_page['results']

     # Looping through orders of each page
      for item in results:
#        sid = item['sid']
        name = item['name'].replace('rktest_','').replace('.yml','')
        platform = item['platform']
        location = item['location']
#        owner = item['owner']
        held_by = item['held_by']
        held_time = item['time_held_by_updated'].replace('T',' ').split('.')[0].replace('Z','')
        held_time_d = datetime.strptime(held_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)

        if (platform == 'PROD_BRIK'):
          time.sleep(0)
          res =  str(sno)+" - name:"+name+", platform:"+platform+", location:"+location
          sno+=1
          if (held_by):
            detail_link = held_by.split('/api')[1]

            try:
              specific = bodega_client.get(detail_link)
              sid = specific['sid']
              if ('owner' in specific):
                owner = specific['owner']
                username = owner['username']
                owner = username
              elif ('cached_build' in specific):
                owner = specific['cached_build']
              # ejection time
              if ('ejection_time' in specific):
                ejection_time = specific['ejection_time'].replace('T',' ').split('.')[0].replace('Z','')
                ejection_time_d = datetime.strptime(ejection_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)
                ejection_period = ejection_time_d - datetime.now()
#                ejection_days = str(ejection_period.days) + ' - ' + str(ejection_time_d)+'-'+str(datetime.now())
                ejection_days = str(ejection_period.days)

              # get the "For " in comments for the long-term reservation justification
              comment=''
              if ('updates' in specific):
                updates = specific['updates']
                for update_item in updates:
                  updateStr = str(update_item['comment']).lower()
                  if (updateStr[0:4] == 'for '):
                    comment = updateStr[4:]
            except:
              owner = " error: cannot fetch: "+detail_link+"\n"
          else:
              owner = "Free"
              sid = "-"

          td = datetime.now() - held_time_d
          tds = str(td.days)

#         set pool from the list of pools
          pool = ''
          if (name in pools):
            pool=pools[name]

          host = hostT(name=name, owner=owner,platform=platform, days=tds, 
                       location=location, ejection=ejection_days, sid=sid, 
                       restime='0', justification=comment, restype='-', 
                       pool=pool)


          hostlist.append(host)
 # End of order loop
      next = order_page['next']
      page+=1


    return hostlist

def readConfig(filename):
    stream = open(filename, "r")
    docs = yaml.load_all(stream)

    for doc in docs:
       for k,v in doc.items():
          for j in v:
            pools[j] = k


def list_orders():
    bodega_client = BodegaClient()
    current_user = bodega_client.get('/profile/')

    user_email = current_user['email']
    order_status = 'OPEN'
    platform = 'PROD_BRIK'
    display = 'TEXT'

    list_orders_int(bodega_client, order_status, display, platform)



def get_mean_order_time(platform, sample_size):
    bodega_client = BodegaClient()
    page = 1
    order_status='FULFILLED'

    try:
      order_page  = bodega_client.get('/orders',
                                      params={'page' : [page],
                                              'status' : [order_status]})
    except:
      print "Retrying fetch..."
      order_page  = bodega_client.get('/orders', 
                                      params={'page' : [page], 
                                              'status' : [order_status]})
    count = order_page['count']
    # goto the bottom 30% of fulfilled orders
    total_pages = (count/10)

    page = int(total_pages*0.4)
    page = 1
    if (DEBUG):
      print ('starting page:'+str(page))
      print('platform filter:'+platform)

    next='temp'
    item_count = 0
    sno = 0
    order_time_filter = datetime.now() - timedelta(hours=36)
    cumulative_time = 0    
    # Looping through pages of orders
    while (next):
      tried = 0
      try:
        order_page  = bodega_client.get('/orders',
                                        params={'page' : [page],
                                                'status' : [order_status],
                                                'time_created__gt': [order_time_filter]
                                            })
      except:
        print "Retrying fetch..."
        order_page  = bodega_client.get('/orders', 
                                        params={'page' : [page], 
                                                'status' : [order_status],
                                                'time_created__gt': [order_time_filter]
                                            })

      count = order_page['count']



      results = order_page['results']


      # Looping through orders of each page
      for item in results:
        fulfilled = item['fulfilled_items']
        sid = item['sid']
        url = item['url']
        owner = item['owner']
        order_time = item['time_created'].replace('T',' ').split('.')[0].replace('Z','')
        tab_priority = item['tab_based_priority']
        order_time_d =  datetime.strptime(order_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)

        # only include fulfilled orders in the last 1 day
        order_age = datetime.now() - order_time_d
        detail_link = url.split('/api')[1]

        specific = bodega_client.get(detail_link)
        sid = specific['sid']
        # Find out platform and location
        fulfilled = specific['fulfilled_items']
        if ('pod' in fulfilled):
          ft = fulfilled['pod']
          plat = ft['platform']
          loc = ft['location']
          net = ft['network']
        else:
          plat='unknown'

        # find fulfilled time
        if ('updates' in specific):
          updates = specific['updates']
          for update_item in updates:
            updateStr = str(update_item['new_status']).lower()
            if ((updateStr == 'fulfilled') and (plat==platform)):
              fulfilled_time = update_item['time_created'].replace('T',' ').split('.')[0].replace('Z','')
              fulfilled_time_d =  datetime.strptime(fulfilled_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)
#              print(' - fulfilled time:'+str(fulfilled_time_d))
              wait_time_d = fulfilled_time_d - order_time_d
              wait_time_ds = wait_time_d.days*86400 + wait_time_d.seconds
              if (DEBUG):
                print('id:'+str(sid)+', platform:'+str(plat)+', location:'+loc+', network:'+str(net)+', order time:'+str(order_time)+', wait time:'+str(wait_time_ds)+', pri:'+str(tab_priority)+', network:'+str(net))

              cumulative_time+=wait_time_ds
              item_count+=1
        else:
           if (DEBUG):
             print('id:'+str(sid)+', platform:'+str(plat)+', location:'+loc+', network:'+str(net)+', order time:'+str(order_time)+', wait time:'+str(wait_time_ds)+', pri:'+str(tab_priority)+', network:'+str(net))
      # End of order loop
      next = order_page['next']

      if (item_count>=sample_size):
        break;

      page+=1
    # End of order page loop
    if (item_count <1):
      average_time = 0
    else:
      average_time = cumulative_time/item_count

    if (DEBUG):
      print('\n')
      print('=== total records: '+str(count)+', sampled:'+str(item_count))
      print('===== average wait time:'+str(average_time))

    return average_time


def readConfig(filename):
    stream = open(filename, "r")
    docs = yaml.load_all(stream)

    for doc in docs:
       for k,v in doc.items():
          for j in v:
            pools[j] = k


def get_order_times(sid):
  bodega_client = BodegaClient()  

  avg_dynapod = 0
  avg_prodbrik = 0


  filename = '/tmp/order-time.yml'
  stream = open(filename, "r")
  docs = yaml.load_all(stream)

  for doc in docs:
    for k,v in doc.items():
      if (k=='dynapod'):
         avg_dynapod = v
      if (k=='prodbrik'):
         avg_prodbrik = v
      if (DEBUG):
        print(k,',',v)
   
  order  = bodega_client.get('/orders/'+sid)


  order_time = order['time_created'].replace('T',' ').split('.')[0].replace('Z','')
  order_time_d =  datetime.strptime(order_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)
  if (DEBUG):
    print('order_time:'+str(order_time_d))

  plat = ''
  loc = ''
  net = ''

  # Find out platform and location
  itemjson = order['items_json']
  plat = itemjson['_item_1']['requirements']['platform']
  loc =  itemjson['_item_1']['requirements']['location']

  if (plat=='DYNAPOD'):
    avg = avg_dynapod
  elif (plat == 'PROD_BROK'):
    avg = avg_dynapod
  else: 
    avg = 0

  avg += (FUDGE)*avg

  if (avg>0):
    target_finish_time = order_time_d + timedelta(seconds=avg)
  else:
    target_finish_time = 0

  return (order_time_d, target_finish_time)


def get_monthly_cost(user_sid):
    bodega_client = BodegaClient()
    page = 1
    order_status='CLOSED'

    page = 1
    if (DEBUG):
      print ('starting page:'+str(page))

    next='temp'
    item_count = 0
    sno = 0

    cumulative_time = 0    
    mdays = datetime.now().day 
    a1stmday = (datetime.now() - timedelta(days=mdays-1))
    a2ndmday = a1stmday - timedelta(days=30)
    a3rdmday = a2ndmday - timedelta(days=30)

    order_time_filter = datetime.now() - timedelta(days=mdays) - timedelta(days=90) 
    cost0=0
    cost1=0
    cost2=0
    cost3=0


    while (next):
      tried = 0
      try:
        order_page  = bodega_client.get('/orders',
                                        params={'page' : [page],
                                                'status' : [order_status],
                                                'time_created__gt': [order_time_filter],
                                                'owner_sid':[user_sid]
                                            })
      except:
        print "Retrying fetch..."
        order_page  = bodega_client.get('/orders', 
                                        params={'page' : [page], 
                                                'status' : [order_status],
                                                'time_created__gt': [order_time_filter],
                                                'owner_sid':[user_sid]
                                            })

      count = order_page['count']
      results = order_page['results']

      # Looping through orders of each page
      for item in results:
        fulfilled = item['fulfilled_items']
        sid = item['sid']

        url = item['url']
        owner = item['owner']
        order_time = item['time_created'].replace('T',' ').split('.')[0].replace('Z','')

        eject = str(item['ejection_time'])
        if (eject != 'None'):
          ejection_time = eject.replace('T',' ').split('.')[0].replace('Z','')
          hours_consumed = (datetime.strptime(ejection_time,"%Y-%m-%d %H:%M:%S") - datetime.strptime(order_time,"%Y-%m-%d %H:%M:%S")).seconds / 3600
        else:
          hours_consumed = 0

        tab_priority = item['tab_based_priority']
        order_time_d =  datetime.strptime(order_time,"%Y-%m-%d %H:%M:%S") - timedelta(hours=8)



        # only include fulfilled orders in the last 1 day
        order_age = datetime.now() - order_time_d
        detail_link = url.split('/api')[1]

        specific = bodega_client.get(detail_link)
        sid = specific['sid']
        ft = 'unknown'
        plat = 'unknown'
        loc = 'unknown'
        net = 'unknown'

        # Find out platform and location
        fulfilled = specific['fulfilled_items']
        if ('pod' in fulfilled):
          ft = fulfilled['pod']
          plat = ft['platform']
          loc = ft['location']
          net = ft['network']
          
        price = specific['total_price']

        if (order_time_d > a1stmday):
          if (DEBUG):
            print 'current_month'
            cost0 += price*hours_consumed
        elif (order_time_d > a2ndmday):
          if (DEBUG):
            print '3rd month'
          cost1 += price*hours_consumed
        elif (order_time_d > a3rdmday):
          if (DEBUG):
            print '2nd month'
          cost2 += price*hours_consumed
        else:
          if (DEBUG):
            print '1th month'
          cost3+=price*hours_consumed

        if (DEBUG):
          print('id:'+str(sid)+', platform:'+str(plat)+', location:'+loc+', network:'+str(net)+', order time:'+str(order_time_d)+',unit price:'+str(price))
          print('  - hours consumed:'+str(hours_consumed))

      # End of order loop
      next = order_page['next']
      page+=1

    if (DEBUG):
      print('\n')
      print('=== total records: '+str(count)+', sampled:'+str(item_count))
      print cost0
      print cost1
      print cost2
      print cost3

     
    return (cost0, cost1, cost2, cost3)
