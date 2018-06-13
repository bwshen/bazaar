export default const liveOrders = {
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "sid": "pyjsei-f3vikoo",
      "url": "https:\/\/bodega.rubrik-lab.com\/api\/orders\/pyjsei-f3vikoo\/?format=json",
      "status": "FULFILLED",
      "items": "{\"_item_1\": {\"requirements\": {\"filename\": \"rktest_B-0686.yml\"}, \"type\": \"rktest_yml\"}}",
      "items_json": {
        "_item_1": {
          "requirements": {
            "filename": "rktest_B-0686.yml"
          },
          "type": "rktest_yml"
        }
      },
      "fulfilled_items": {
        "_item_1": {
          "sid": "cvu6js-s2r44rw",
          "url": "https:\/\/bodega.rubrik-lab.com\/api\/items\/cvu6js-s2r44rw\/?format=json",
          "name": "Item(sid=cvu6js-s2r44rw)",
          "held_by": "https:\/\/bodega.rubrik-lab.com\/api\/orders\/pyjsei-f3vikoo\/?format=json",
          "time_held_by_updated": "2018-06-12T01:24:35.800000Z",
          "state": "ACTIVE",
          "specific_item": "https:\/\/bodega.rubrik-lab.com\/api\/rktest_ymls\/cvu6js-s2r44rw\/?format=json"
        }
      },
      "ejection_time": "2018-06-14T05:24:35.776666Z",
      "expiration_time": "2018-06-13T01:03:47.113333Z",
      "expiration_time_limit": "1 00:00:00",
      "maintenance": false,
      "time_limit": "2 04:00:00",
      "owner": {
        "sid": "ubipme-jspzqbi",
        "url": "https:\/\/bodega.rubrik-lab.com\/api\/users\/ubipme-jspzqbi\/?format=json",
        "username": "andrew.chan",
        "first_name": "Andrew",
        "last_name": "Chan",
        "email": "andrew.chan@rubrik.com",
        "is_superuser": false,
        "live_orders": "https:\/\/bodega.rubrik-lab.com\/api\/orders\/?format=json?owner_sid=ubipme-jspzqbi&status_live=True"
      },
      "time_created": "2018-06-12T01:03:47.113333Z",
      "time_last_updated": "2018-06-13T21:25:11.070000Z",
      "tab": {
        "sid": "edxvwo-jqtjmu6",
        "url": "https:\/\/bodega.rubrik-lab.com\/api\/tabs\/edxvwo-jqtjmu6\/?format=json",
        "limit": 1,
        "owner": "https:\/\/bodega.rubrik-lab.com\/api\/users\/ubipme-jspzqbi\/?format=json",
        "charged_live_orders": "https:\/\/bodega.rubrik-lab.com\/api\/orders\/?format=json?tab_sid=edxvwo-jqtjmu6&status_live=True"
      },
      "tab_based_priority": -1
    }
  ]
};
