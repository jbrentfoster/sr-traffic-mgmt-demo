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
import logging
import com.cisco.wae.design
from com.cisco.wae.design import ServiceConnectionManager
from com.cisco.wae.design.model.net import TrafficLevelKey, ColumnRecord, ColumnType, ReportTable, ReportRecord, \
    ReportKey
from com.cisco.wae.design.sim import FailureScenarioRecord
from com.cisco.wae.design.model.net import NodeKey
from com.cisco.wae.design.model.net import DemandKey
from com.cisco.wae.design.model.net import DemandEndpointKey
from com.cisco.wae.design.model.net import ServiceClassKey
from com.cisco.wae.design.model.net import LSPKey
from com.cisco.wae.design.model.net import LSPType
from com.cisco.wae.design.model.traffic import DemandTrafficKey
from com.cisco.wae.design.model.net import TrafficLevelKey
from com.cisco.wae.design.model.net import DemandRecord
from com.cisco.wae.design.model.net import ServiceClassRecord
from com.cisco.wae.design.model.net import LSPRecord
from com.cisco.wae.design.tools import FRRLSPInitializerOptions
from com.cisco.wae.design.tools import SimAnalysisOptions, SAFailureType
from com.cisco.wae.design.model import PlanFormat
from com.cisco.wae.design.model.net import SegmentList
from com.cisco.wae.design.model.net import SegmentListKey
from com.cisco.wae.design.model.net import SegmentListManager
from com.cisco.wae.design.model.net import SegmentListRecord
from com.cisco.wae.design.model.net import SegmentListHopRecord
from com.cisco.wae.design.model.net import SegmentListHopType
from com.cisco.wae.design.model.net import NamedPathRecord
from com.cisco.wae.design.model.net import LSPPathRecord
import Ice
import json
import random


host = "10.135.7.127"
port = "30744"
protocol = 'ssl'
conn = com.cisco.wae.design.ServiceConnectionManager.newServiceConnection(host, port, protocol)

def run_simulation(traffic_data):
    global conn
    with open('plan_files/lab_topology_SR_FlexAlgo_renamed.pln', 'rb') as f:
        plan = conn.getPlanManager().newPlanFromBytes(f.read())
        f.close()
    net = plan.getNetwork()

    with open('jsonfiles/aac_map.json', 'r') as file:
        aac_map = json.load(file)

    with open('jsonfiles/sid_map.json', 'r') as file:
        sid_map = json.load(file)

    with open('jsonfiles/node_name_lookup.json', 'r') as file:
        node_names = json.load(file)

    for demand in traffic_data:
        nodeA = demand['source_router']
        nodeB = demand['dest_router']
        bw_A_B = demand['traffic_rate']
        demand_name_A_B = demand['demand_name']
        try:
            lsp_name = new_sr_lsp(plan, src_node=nodeA, dest_node=nodeB, dest_sid=sid_map[demand['locator_addr']][0],
                                  dest_locator_addr=demand['locator_addr'])
            tmp_dmd = new_demand_for_LSP(plan, nodeA, nodeB, lsp_name, demand_name_A_B, bw_A_B)
        except Exception as err:
            if nodeB in aac_map:
                nodeB_aac = aac_map[nodeB]
                lsp_name = new_sr_lsp(plan, src_node=nodeA, dest_node=nodeB_aac,
                                      dest_sid=sid_map[demand['locator_addr']][0],
                                      dest_locator_addr=demand['locator_addr'])
                tmp_dmd = new_demand_for_LSP(plan, nodeA, nodeB_aac, lsp_name, demand_name_A_B, bw_A_B)

    selected_circuits = net.getCircuitManager().getAllCircuits()

    # Now that the circuits are chosen, create a dictionary of dictionaries using
    # the circuitKeys as the key values
    circuit_data = {}
    for circuit_key, circuit in selected_circuits.items():
        circuit_data[circuit_key] = {}
        circuit_data[circuit_key]['circuit'] = circuit
    try:
        interface_data = get_util_interfaces(conn, plan, circuit_data)
    except Ice.ConnectionLostException  as err:
        logging.error(err)
        logging.info("Creating new Crosswork connection...")
        conn = com.cisco.wae.design.ServiceConnectionManager.newServiceConnection(host, port, protocol)

    logging.info("Simulation analysis completed.")


    node_manager = plan.getNetwork().getNodeManager()
    node_map = node_manager.getAllNodes()
    node_coordinates = {}
    for node_key, node in node_map.items():
        latitude = node.getLatitude()
        longitude = node.getLongitude()
        node_coordinates[node_key] = (latitude, longitude)

    try:
        serialized_bytes = plan.serializeToBytesForVersion(PlanFormat.PlnFile, '7.5')
        # serialized_bytes = plan.serializeToBytes(PlanFormat.PlnFile)
        with open("plan_files/plan_out.pln", "wb") as file:
            file.write(serialized_bytes)
        logging.info("Serialized plan file to bytes.")
    except Exception as err:
        logging.error("Could not save the plan file to file system!")

    return interface_data


def new_sr_lsp(plan, src_node, dest_node, dest_sid, dest_locator_addr):
    random_num = random.random()
    hop_type = SegmentListHopType.SEGMENTLISTHOPTYPE_NODE
    segment_list_hop_rec = SegmentListHopRecord(
        hopType=hop_type,
        nodeHop=NodeKey(dest_node),
        sid=int(dest_sid),
    )
    segment_list_hop_rec_list = []
    segment_list_hop_rec_list.append(segment_list_hop_rec)
    segment_list_name = f"{src_node}-{dest_node}-{dest_locator_addr}"
    segment_list_rec = SegmentListRecord(
        name=segment_list_name,
        sourceKey=NodeKey(src_node),
        hops=segment_list_hop_rec_list,
    )
    segment_list_manager = plan.getNetwork().getSegmentListManager()
    # sl_key = SegmentListKey(name=segment_list_name,sourceKey=NodeKey(src_node))
    # if segment_list_manager.hasSegmentList(sl_key):
    #     segment_list = segment_list_manager.getSegmentList(sl_key)
    # else:
    segment_list = segment_list_manager.newSegmentList(segment_list_rec)
    # lsp_name = f"{src_node}-{dest_node}-{dest_sid}--{random_num}"
    lsp_name = f"{src_node}-{dest_node}-{dest_locator_addr}"
    lspRec = LSPRecord(
        sourceKey=NodeKey(name=src_node),
        name=lsp_name,
        destinationKey=NodeKey(name=dest_node),
        isActive=True,
        isPrivate=True,
        type=LSPType.SegmentRouting,
    )
    lspMgr = plan.getNetwork().getLSPManager()
    lsp = lspMgr.newLSP(lspRec)

    lspRecord = lsp.getRecord()
    lspKey = lsp.getKey()

    lspPathRecord = LSPPathRecord(
        lKey=lspKey,
        pathOption=1,
        segListKey=segment_list.getKey(),
        active=True,
    )
    lspPathManager = plan.getNetwork().getLSPPathManager()
    lspPath = lspPathManager.newLSPPath(lspPathRecord)
    return lsp_name


def new_demand_for_LSP(id, src, dest, lspName, demandName, val):
    serviceClass = 'Default'
    serviceClassMgr = id.getNetwork().getServiceClassManager()
    serviceClassExists = serviceClassMgr.hasServiceClass(
        ServiceClassKey(name=serviceClass))
    if not serviceClassExists:
        serviceClassRecord = ServiceClassRecord(name=serviceClass)
        serviceClassMgr.newServiceClass(serviceClassRecord)

    # keylist = serviceClassMgr.getAllServiceClassKeys()
    dmdRec = DemandRecord(
        name=demandName,
        source=DemandEndpointKey(key=src),
        destination=DemandEndpointKey(key=dest),
        serviceClass=ServiceClassKey(name='Default'),
        privateLSP=LSPKey(
            name=lspName,
            sourceKey=NodeKey(name=src)
        )
    )
    dmdMgr = id.getNetwork().getDemandManager()
    new_demand = dmdMgr.newDemand(dmdRec)

    dmdTraffKey = DemandTrafficKey(
        traffLvlKey=TrafficLevelKey(name='Default'),
        dmdKey=DemandKey(
            name=demandName,
            source=DemandEndpointKey(key=src),
            destination=DemandEndpointKey(key=dest),
            serviceClass=ServiceClassKey(name='Default'),
        )
    )
    dmdTrafficMgr = id.getTrafficManager().getDemandTrafficManager()
    dmdTrafficMgr.setTraffic(dmdTraffKey, val)
    dmdTrafficMgr.setGrowthPercent(dmdTraffKey, 10.0)

    return new_demand


def get_util_interfaces(conn, plan, circuit_data):
    # Initialize network object
    network = plan.getNetwork()
    # Initialize sim object
    tool_mgr = conn.getToolManager()
    sim = tool_mgr.newSimAnalysis()

    print("Running new simulation...")
    sim_options = SimAnalysisOptions(
        failures=[SAFailureType.SA_FAILURETYPE_CIRCUITS]
        # failures=[SAFailureType.SA_FAILURETYPE_CIRCUITS,
        #           SAFailureType.SA_FAILURETYPE_NODES]
    )
    sim.run(network, sim_options)
    interface_dict = {}
    # obtain highest wcUtil results per circuit
    for circuit in circuit_data.keys():
        intf_list = [circuit.interfaceAKey, circuit.interfaceBKey]
        for intf in intf_list:
            # Set other_intf as the one not currently used
            other_intf = circuit.interfaceBKey if intf == circuit.interfaceAKey else circuit.interfaceAKey
            wc_result_recs = sim.getInterfaceWCRecords(intf)
            for wc_result in wc_result_recs:
                if wc_result != Ice.Unset:
                    try:
                        if wc_result.wcTraffic > interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                            'worst-case-traffic']:
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'worst-case-traffic'] = int(wc_result.wcTraffic)
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'worst-case-util'] = round(wc_result.wcUtil,1)
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'failure-scenario'] = wc_result.failureScenario
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'neighbor'] = other_intf.sourceKey.name
                    except Exception as err:
                        try:
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name] = {
                                'worst-case-traffic': int(wc_result.wcTraffic)}
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'worst-case-util'] = round(wc_result.wcUtil,1)
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'failure-scenario'] = wc_result.failureScenario
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'neighbor'] = other_intf.sourceKey.name
                        except Exception as err:
                            try:
                                interface_dict[wc_result.iface.sourceKey.name] = {
                                    wc_result.iface.name: {'worst-case-traffic': int(wc_result.wcTraffic)}}
                                interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                    'worst-case-util'] = round(wc_result.wcUtil,1)
                                interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                    'failure-scenario'] = wc_result.failureScenario
                                interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                    'neighbor'] = other_intf.sourceKey.name
                            except Exception as err:
                                logging.info(f"Could not get worst-case-traffic for {circuit}")
    sim = conn.getSimulationManager()
    r_sim = sim.newRouteSimulation(plan, FailureScenarioRecord())
    trf_sim = sim.newTrafficSimulation(r_sim, plan.getNetwork().getTrafficLevelManager().getTrafficLevel(
        TrafficLevelKey(name='Default')), None)
    for circuit in circuit_data.keys():
        intf_list = [circuit.interfaceAKey, circuit.interfaceBKey]
        for intf in intf_list:
            simulated_traff_map = trf_sim.getInterfacesSimulatedTrafficRecords([intf])
            for interface_key, int_sim_traff_record in simulated_traff_map.items():
                if int_sim_traff_record != Ice.Unset:
                    try:
                        interface_dict[int_sim_traff_record.ifaceKey.sourceKey.name][
                            int_sim_traff_record.ifaceKey.name][
                            'traffic'] = int(int_sim_traff_record.trafficSim)
                        interface_dict[int_sim_traff_record.ifaceKey.sourceKey.name][
                            int_sim_traff_record.ifaceKey.name][
                            'capacity'] = int(int_sim_traff_record.capacitySim)
                        interface_dict[int_sim_traff_record.ifaceKey.sourceKey.name][
                            int_sim_traff_record.ifaceKey.name][
                            'util'] = round(int_sim_traff_record.utilSim,1)
                    except Exception as err:
                        logging.info(f"Could not get traffic for {circuit}")
    return interface_dict


if __name__ == '__main__':
    main()
