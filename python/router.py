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

class Router:
    def __init__(self, router_id, locator=None):
        """
        Initialize a Router instance.

        :param router_id: The host name of the router.
        :param locator: Optional locator information for the router.
        """
        self.router_id = router_id
        self.locator = locator  # New attribute
        self.locator_intf = {}
        self.neighbors = []
        self.latest_time_stamp = None

    def set_locator(self, locator):
        """
        Set or update the locator for the router.

        :param locator: The locator information to set.
        """
        self.locator = locator

    def get_latest_time_stamp(self):
        return self.latest_time_stamp

    def get_locator(self):
        """
        Get the locator information for the router.

        :return: The current locator information.
        """
        return self.locator

    def add_intf_locator(self, intf_name, locator_addr, moving_average, time_stamp):
        """
        Add a locator with its moving average in Gbps to the locator list.
        If the locator already exists, update its moving average.

        :param locator_addr: The address of the locator.
        :param moving_average_gbps: The moving average in Gbps.
        """

        try:
            self.locator_intf[intf_name][locator_addr] = {'rate': moving_average, 'time_stamp': time_stamp}
            self.latest_time_stamp = time_stamp
            # logging.info(f"Did not have create new entry for {self.router_id}, {intf_name}.)
        except KeyError:
            self.locator_intf[intf_name] = {locator_addr: {'rate': moving_average, 'time_stamp': time_stamp}}
            self.latest_time_stamp = time_stamp
            # logging.info(
            # f"Created new entry for {self.router_id}, {intf_name}.  Adding new locator {locator_addr}")

    def get_intf_locator(self, intf_name, locator_addr):
        try:
            return self.locator_intf[intf_name][locator_addr]['rate'], self.locator_intf[intf_name][locator_addr]['time_stamp']
        except KeyError:
            return 0,0

    def sum_locators_for_address(self, locator_addr):
        """
        Return the sum of all locators in 'locator_intf' that match the input 'locator_addr'.

        :param locator_addr: The address of the locator to sum.
        :return: The sum of moving_average_gbps for the specified locator address.
        """
        total = 0
        for intf in self.locator_intf.values():
            if locator_addr in intf:
                total += intf[locator_addr]['rate']
        return total

    def add_neighbor(self, neighbor_id, remote_intf_name):
        """
        Add a neighbor to the neighbors list.

        :param neighbor_id: The ID of the neighbor router.
        :param intf_name: The remote interface on this neighbor.
        """
        neighbor_entry = {
            'neighbor_id': neighbor_id,
            'remote_intf_name': remote_intf_name,
        }
        self.neighbors.append(neighbor_entry)

    def del_intf_locator(self):
        """
        Reset the 'locator_intf' dictionary.
        """
        self.locator_intf = {}