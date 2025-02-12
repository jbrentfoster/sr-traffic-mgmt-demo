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

from collections import deque
import logging


class RouterInterfaceMonitor:
    def __init__(self):
        # Dictionary to store data for each interface
        self.data_store = {}
        # Attribute to store the latest time stamp
        self.latest_time_stamp = None

    # def get_moving_average_gps(self, router_id, interface_id, locator_addr):
    #     # Retrieve the moving average gps for a specific router interface and locator address
    #     key = (router_id, interface_id, locator_addr)
    #     if key in self.data_store:
    #         return self.data_store[key]['moving_average_gps']
    #     else:
    #         return None

    # TODO Figure out how to use the time_stamp
    def update_data(self, router_id, interface_id, locator_addr, new_byte_count, time_stamp):
        # Ensure the router_id entry exists
        if router_id not in self.data_store:
            self.data_store[router_id] = {}

        # Ensure the interface_id entry exists
        if interface_id not in self.data_store[router_id]:
            self.data_store[router_id][interface_id] = {}

        # Ensure the locator_addr entry exists
        if locator_addr not in self.data_store[router_id][interface_id]:
            self.data_store[router_id][interface_id][locator_addr] = {
                'data_points': deque(maxlen=5),  # FIFO queue with a max size of 5
                'moving_average_gbps': 0,
                'time_stamp': time_stamp
            }

        # Get the existing data for the interface
        interface_data = self.data_store[router_id][interface_id][locator_addr]

        if len(interface_data['data_points']) > 0:
            previous_byte_count = interface_data['data_points'][-1][1]
        else:
            previous_byte_count = 0
        # Add new data point
        if new_byte_count < previous_byte_count:
            logging.info(
                f"Bad data-point: {router_id}, {interface_id}, {locator_addr}, Byte count: {new_byte_count}, Time stamp: {time_stamp}, Previous byte count: {interface_data['data_points'][-1]}")
            interface_data['data_points'].clear()
            # del self.data_store[router_id][interface_id][locator_addr]
            # self.data_store[router_id][interface_id][locator_addr] = {
            #     'data_points': deque(maxlen=5),  # FIFO queue with a max size of 5
            #     'moving_average_gbps': 0,
            #     'time_stamp': time_stamp}

        interface_data['data_points'].append((time_stamp, new_byte_count))

        # Update the latest time stamp
        self.latest_time_stamp = time_stamp

        # Calculate moving average in bps
        if len(interface_data['data_points']) > 1:
            # Calculate differences between consecutive data points
            differences = [(t2 - t1, b2 - b1) for (t1, b1), (t2, b2) in
                           zip(interface_data['data_points'], list(interface_data['data_points'])[1:])]
            # Calculate the average rate
            total_bytes = sum(diff[1] for diff in differences)
            total_time = sum(diff[0] for diff in differences)
            if total_time > 0:
                interface_data['moving_average_gbps'] = int(
                    ((total_bytes * 8) / total_time) / 10 ** 6) # Convert bytes to bits and compute rate
            else:
                interface_data['moving_average_gbps'] = 0
        # logging.info(
        #     f"Router: {router_id} Interface: {interface_id}, Locator: {locator_addr}  Moving Average: {interface_data['moving_average_gbps']} Gbps")
        # Remove outdated entries older than 150 seconds
        # self._remove_outdated_entries(150)

    #TODO this does not work to purge out-dated entries, need to debug
    # def _remove_outdated_entries(self, time_delta):
    #     # Iterate through the data_store and remove entries with time_stamp older than the threshold
    #     if self.latest_time_stamp is not None:
    #         for router_id in list(self.data_store.keys()):
    #             for interface_id in list(self.data_store[router_id].keys()):
    #                 for locator_addr in list(self.data_store[router_id][interface_id].keys()):
    #                     interface_data = self.data_store[router_id][interface_id][locator_addr]
    #                     if interface_data['data_points'] and (
    #                             self.latest_time_stamp - interface_data['data_points'][-1][0] > time_delta):
    #                         del self.data_store[router_id][interface_id][locator_addr]
    #                 if not self.data_store[router_id][interface_id]:
    #                     del self.data_store[router_id][interface_id]
    #             if not self.data_store[router_id]:
    #                 del self.data_store[router_id]

    def get_unique_locator_addrs(self):
        # Set to store unique locator addresses
        unique_addrs = set()
        # Traverse the nested dictionary to collect all unique locator addresses
        for router_data in self.data_store.values():
            for interface_data in router_data.values():
                unique_addrs.update(interface_data.keys())
        # Return the unique addresses as a list
        return list(unique_addrs)

    def get_entries_by_router_id(self, router_id):
        # Method to get all entries for a given router_id
        if router_id not in self.data_store:
            return []

        entries = []
        for interface_id, interfaces in self.data_store[router_id].items():
            for locator_addr, data in interfaces.items():
                entry = {
                    'locator_addr': locator_addr,
                    'interface_id': interface_id,
                    'moving_average_gbps': data['moving_average_gbps'],
                    'time_stamp': data['time_stamp']
                }
                entries.append(entry)
        return entries
