"""

Copyright (c) 2025 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""
import asyncio
import json
import logging
from python import router
from python import router_interface_monitor
from python import traffic_matrix
from python import utils
from python import crosswork_planning
import dateutil

# Globals
monitor = router_interface_monitor.RouterInterfaceMonitor()
router_dict = {}
local_traffic_matrix = traffic_matrix.TrafficMatrix()

with open('jsonfiles/node_neighbors.json', 'r') as file:
    file_dict = json.load(file)

# Build the router inventory stored as router_dict
for router_id, attributes in file_dict.items():
    tmp_router = router.Router(router_id)
    tmp_router.set_locator(attributes['locator'])
    for neighbor in attributes['neighbors']:
        tmp_router.add_neighbor(neighbor['hostname'], neighbor['intf_name'])
    router_dict[router_id] = tmp_router


async def traffic_matrix_updater(websockets):
    global router_dict
    global local_traffic_matrix
    global monitor

    # Define the base URL and parameters
    influx_query_url = 'http://10.135.7.178:8086/query'
    influx_write_url = 'http://10.135.7.178:8086/write?db=telegraf'
    with open('templates/query_template.txt', 'r') as file:
        query_template = file.read().strip()
    with open('templates/write_template.txt', 'r') as file:
        write_template = file.read().strip()
    count = 0
    good_collection_count = 0
    while True:
        bad_data_count = 0
        logging.info("Traffic matrix updater thread is running...")
        await asyncio.sleep(30)
        # query the influxdb for locator counters
        for router, attributes in router_dict.items():
            query_formatted = query_template.format(hostname=router)
            params = {
                'pretty': 'true',
                'db': 'telegraf',
                'q': query_formatted
            }
            response = await utils.rest_get_tornado_httpclient(influx_query_url, data=params)
            try:
                response_dict = json.loads(response)
            except Exception as err:
                pass
            try:
                for data_point in response_dict['results'][0]['series']:
                    # logging.info(
                    #     f"{router}, {data_point['tags']['accounting_information/outgoing_interface']}, {data_point['tags']['ipv6_address']}, time-stamp: {data_point['values'][0][0]} bytes: {data_point['values'][0][1]}")
                    good_data = process_influx_locator(data_point)
                    if not good_data:
                        bad_data_count += 1
                        good_collection_count = 0
                        monitor.del_all_data()
                        logging.info("Bad data detected, will not process traffic matrix.")
            except Exception as err:
                logging.info(f"Could not get data for {router}")

        if bad_data_count == 0:
            good_collection_count += 1
            logging.info(f"Good collection cycles completed: {good_collection_count}")

        # if multiple good collections, compute the traffic matrix
        if good_collection_count >= 3:
            # compute new trafic matrix
            local_traffic_matrix = traffic_matrix.TrafficMatrix()
            for locator_addr in monitor.get_unique_locator_addrs():
                update_traffic_matrix(locator_addr)
            message = {'target': 'traffic', 'data': local_traffic_matrix.get_traffic_entries()}
            message_json = json.dumps(message, indent=2, sort_keys=True)
            # write to websocket updated traffic matrix
            for ws in websockets:
                ws.send_message(message_json)
            # write the traffic matrix to a file
            with open('jsongets/traffic_matrix.json', 'w') as file:
                json.dump(local_traffic_matrix.get_traffic_entries(), file, indent=4)

            # Run simulation analysis through crosswork planning
            logging.info("Running simulation analysis with Crosswork Planning...")
            intf_data = crosswork_planning.run_simulation(local_traffic_matrix.get_traffic_entries())
            message = {'target': 'interface', 'data': intf_data}
            message_json = json.dumps(message, indent=2, sort_keys=True)
            # write to websocket updated traffic matrix
            for ws in websockets:
                ws.send_message(message_json)
            # write interface data to a file
            with open('jsongets/interface_data.json', 'w') as file:
                json.dump(intf_data, file, indent=4)

            # write to InfluxDB
            for router, router_attr in intf_data.items():
                for intf, intf_attr in router_attr.items():
                    write_data = write_template.format(router_id=router, intf_name=intf,
                                                       wc_traffic=intf_attr['worst-case-traffic'])
                    await utils.rest_post_tornado_httpclient(influx_write_url, data=write_data)

            # clear interface data from all routers
            for router, attributes in router_dict.items():
                attributes.del_intf_locator()
            count += 1
            # periodically clear out entries in the traffic monitor older than 300 seconds
            if count % 10 == 0:
                logging.info("Purging outdated entries in traffic monitor...")
                monitor.remove_outdated_entries(300)


# def run_in_thread():
#     # Create a new asyncio event loop for this thread
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     # Run the consumer in the asyncio event loop
#     loop.run_until_complete(traffic_matrix_updater())


def process_influx_locator(data):
    good_data = True
    telemetry_encoding_path = "Cisco-IOS-XR-fib-common-oper:cef-accounting/vrfs/vrf/afis/afi/pfx/srv6locs/srv6loc"
    try:
        if data["name"] == telemetry_encoding_path and "tags" in data:
            try:
                router_id = data['tags']['source']
                if_name = data['tags']['accounting_information/outgoing_interface']
                output_bytes = data['values'][0][1]
                locator_addr = data['tags']['ipv6_address']
                time_stamp = rfc3339_to_epoch(data['values'][0][0])
                good_data, moving_average = monitor.update_data(router_id, if_name, locator_addr, output_bytes,
                                                                time_stamp)
                if good_data:
                    router_dict[router_id].add_intf_locator(if_name, locator_addr, moving_average, time_stamp)
            except Exception as err:
                logging.info(f"Exception processing influx data for {router}")
    except Exception as err:
        logging.info("Invalid message from influx.")
    return good_data


def update_traffic_matrix(locator_addr):
    for router_id, router in router_dict.items():
        router_total = router.sum_locators_for_address(locator_addr)
        router_time_stamp = router.get_latest_time_stamp()

        if router_total > 0:
            neighbors_total = 0
            # find all neighbors with locator and get traffic rate
            for neighbor in router.neighbors:
                neighbor_total = router_dict[neighbor['neighbor_id']].get_intf_locator(neighbor['remote_intf_name'],
                                                                                       locator_addr)[0]
                neighbors_total += neighbor_total
            external_traffic = router_total - neighbors_total
            if external_traffic >= 1000:  # Ignore anything less than 1000 Mbps
                logging.info(f"Router {router_id} is the source of {external_traffic} Mbps to locator {locator_addr}.")
                dest_router_id = get_router_id_from_locator(locator_addr)
                local_traffic_matrix.add_traffic_entry(router_id, dest_router_id, locator_addr, external_traffic)


def rfc3339_to_epoch(rfc3339_string):
    # Parse the RFC 3339 date-time string into a datetime object
    dt = dateutil.parser.isoparse(rfc3339_string)

    # Convert the datetime object to epoch time (Unix timestamp)
    epoch_time = int(dt.timestamp())
    return epoch_time


def get_router_id_from_locator(locator_addr):
    tmp_locator_id = locator_addr.split(':')[2]
    for router, attributes in router_dict.items():
        if tmp_locator_id == attributes.locator:
            return router
    return "unknown"
