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

class TrafficMatrix:
    def __init__(self):
        """
        Initialize the TrafficMatrix instance with an empty list of traffic entries.
        """
        self.traffic_entries = []

    def add_traffic_entry(self, source_router, dest_router, locator_addr, traffic_rate, algo_name, demand_name):
        """
        Add a traffic entry to the traffic list. If an entry with the same
        source_router and locator_addr exists, update the traffic rate.

        :param demand_name: The name of the demand
        :param algo_name: The name of associated FlexAlgo
        :param source_router: The identifier of the source router.
        :param locator_addr: The address of the locator.
        :param traffic_rate: The traffic rate in Gbps (as an integer)
        """
        for entry in self.traffic_entries:
            if entry['source_router'] == source_router and entry['locator_addr'] == locator_addr:
                entry['traffic_rate'] = traffic_rate
                return

        # If no existing entry is found, add a new one
        new_entry = {
            'source_router': source_router,
            'dest_router': dest_router,
            'locator_addr': locator_addr,
            'traffic_rate': traffic_rate,
            'algo_name': algo_name,
            'demand_name': demand_name
        }
        self.traffic_entries.append(new_entry)

    def get_traffic_for_router(self, source_router):
        """
        Retrieve all traffic entries for a specific source router.

        :param source_router: The identifier of the source router.
        :return: A list of traffic entries for the specified router.
        """
        return [entry for entry in self.traffic_entries if entry['source_router'] == source_router]

    def get_total_traffic(self):
        """
        Calculate the total traffic rate for all entries.

        :return: The total traffic rate in Gbps as an integer.
        """
        return sum(entry['traffic_rate'] for entry in self.traffic_entries)

    def get_traffic_entries(self):
        # Return the traffic_entries list
        return self.traffic_entries

    def __repr__(self):
        """
        Return a string representation of the TrafficMatrix instance.
        """
        return f"TrafficMatrix(traffic_entries={self.traffic_entries})"