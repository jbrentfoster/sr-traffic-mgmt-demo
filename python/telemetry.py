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
from aiokafka import AIOKafkaConsumer
import json
import logging
from collections import deque
import threading
from python import router
from python import router_interface_monitor
from python import traffic_matrix

# TODO figure out how to purge stale/non-existent locators from routers
# Globals
monitor = router_interface_monitor.RouterInterfaceMonitor()
router_dict = {}
local_traffic_matrix = traffic_matrix.TrafficMatrix()
websockets_tmp = []
KAFKA_TOPIC = 'telegraf'
KAFKA_BOOTSTRAP_SERVER = '10.135.7.105:9092'

with open('jsonfiles/node_neighbors.json', 'r') as file:
    file_dict = json.load(file)

for router_id, attributes in file_dict.items():
    tmp_router = router.Router(router_id)
    tmp_router.set_locator(attributes['locator'])
    for neighbor in attributes['neighbors']:
        tmp_router.add_neighbor(neighbor['hostname'], neighbor['intf_name'])
    router_dict[router_id] = tmp_router


async def traffic_matrix_updater():
    global router_dict
    global local_traffic_matrix
    global monitor

    while True:
        logging.info("Traffic matrix updater thread is running...")
        await asyncio.sleep(30)
        local_traffic_matrix = traffic_matrix.TrafficMatrix()
        for locator_addr in monitor.get_unique_locator_addrs():
            update_traffic_matrix(locator_addr)
        for ws in websockets_tmp:
            ws.send_message(json.dumps(local_traffic_matrix.get_traffic_entries(), indent=2, sort_keys=True))
        with open('jsongets/traffic_matrix.json', 'w') as file:
            json.dump(local_traffic_matrix.get_traffic_entries(), file, indent=4)


def run_in_thread():
    # Create a new asyncio event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the consumer in the asyncio event loop
    loop.run_until_complete(traffic_matrix_updater())


async def consume(websockets):
    global router_dict
    global local_traffic_matrix
    global monitor
    global websockets_tmp

    websockets_tmp = websockets

    # monitor = RouterInterfaceMonitor()
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
    )
    await consumer.start()
    logging.info("Kafka consumer has started")

    thread = threading.Thread(target=run_in_thread)
    thread.start()

    logging.info("Listening for messages...")
    try:
        async for message in consumer:
            message_dict = json.loads(message.value.decode("utf-8", errors='ignore'))
            logging.debug("Message received from kafka...")
            process_telemetry_msg_locator(message_dict)
    finally:
        logging.info("Halting telemetry processing...")
        await consumer.stop()


def process_telemetry_msg_locator(msg):
    telemetry_encoding_path = "Cisco-IOS-XR-fib-common-oper:cef-accounting/vrfs/vrf/afis/afi/pfx/srv6locs/srv6loc"
    try:
        # logging.info("Kafka message is from " + msg['tags']['source'] + "...")
        if msg["name"] == telemetry_encoding_path and "fields" in msg:
            try:
                router_id = msg['tags']['source']
                if_name = msg['tags']['accounting_information/outgoing_interface']
                output_bytes = msg['fields']['accounting_information/number_of_tx_bytes']
                locator_addr = msg['tags']['ipv6_address']
                time_stamp = msg['timestamp']
                # if output_bytes > 0:
                msg_text = f"Kafka message: {msg['tags']['source']} {locator_addr} {if_name} output bytes: {output_bytes}"
                # logging.info(msg_text)
                monitor.update_data(router_id, if_name, locator_addr, output_bytes, time_stamp)
                entries = monitor.get_entries_by_router_id(router_id)
                for entry in entries:
                    router_dict[router_id].add_intf_locator(entry['interface_id'], entry['locator_addr'],
                                                            entry['moving_average_gbps'])
                # update_traffic_matrix(locator_addr)
                pass
            except Exception as err:
                pass
    except Exception as err:
        pass
        logging.info("Invalid message from kafka.")


def update_traffic_matrix(locator_addr):
    for router_id, router in router_dict.items():
        router_total = router.sum_locators_for_address(locator_addr)
        if router_total > 0:
            neighbors_total = 0
            # find all neighbors with locator and get traffic rate
            for neighbor in router.neighbors:
                neighbors_total += router_dict[neighbor['neighbor_id']].get_intf_locator(neighbor['remote_intf_name'],
                                                                                         locator_addr)
            external_traffic = router_total - neighbors_total
            if external_traffic > 500:  # Ignore anything less than 500 Mbps
                logging.info(f"Router {router_id} is the source of {external_traffic} Gbps to locator {locator_addr}.")
                dest_router_id = get_router_id_from_locator(locator_addr)
                local_traffic_matrix.add_traffic_entry(router_id, dest_router_id, locator_addr, external_traffic)


def nested_keys_exist(nested_dict, keys):
    """
    Check if a sequence of keys exists in a nested dictionary.

    :param nested_dict: The dictionary to search.
    :param keys: A list or tuple of keys representing the path in the dictionary.
    :return: True if all keys exist, False otherwise.
    """
    current_dict = nested_dict
    for key in keys:
        if isinstance(current_dict, dict) and key in current_dict:
            current_dict = current_dict[key]
        else:
            return False
    return True


def get_router_id_from_locator(locator_addr):
    tmp_locator_id = locator_addr.split(':')[2]
    for router, attributes in router_dict.items():
        if tmp_locator_id == attributes.locator:
            return router
    return "unknown"
