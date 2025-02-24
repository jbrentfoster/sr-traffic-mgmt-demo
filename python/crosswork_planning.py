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


def run_simulation(traffic_data):
    conn = com.cisco.wae.design.ServiceConnectionManager.newServiceConnection(host, port, protocol)
    with open('plan_files/lab_topology_SR_FlexAlgo.pln', 'rb') as f:
        plan = conn.getPlanManager().newPlanFromBytes(f.read())
        f.close()
    net = plan.getNetwork()

    with open('jsonfiles/aac_map.json', 'r') as file:
        aac_map = json.load(file)

    with open('jsonfiles/sid_map.json', 'r') as file:
        sid_map = json.load(file)

    for demand in traffic_data:
        nodeA = demand['source_router']
        nodeB = demand['dest_router']
        bw_A_B = demand['traffic_rate']
        try:
            demand_name_A_B = nodeA + demand['locator_addr'] + nodeB
            lsp_name = new_sr_lsp(plan, src_node=nodeA, dest_node=nodeB, dest_sid=sid_map[demand['locator_addr']])
            tmp_dmd = new_demand_for_LSP(plan, nodeA, nodeB, lsp_name, demand_name_A_B, bw_A_B)
        except Exception as err:
            if nodeB in aac_map:
                nodeB_aac = aac_map[nodeB]
                demand_name_A_B = nodeA + demand['locator_addr'] + nodeB_aac
                lsp_name = new_sr_lsp(plan, src_node=nodeA, dest_node=nodeB_aac,
                                      dest_sid=sid_map[demand['locator_addr']])
                tmp_dmd = new_demand_for_LSP(plan, nodeA, nodeB_aac, lsp_name, demand_name_A_B, bw_A_B)

    selected_circuits = net.getCircuitManager().getAllCircuits()

    # Now that the circuits are chosen, create a dictionary of dictionaries using
    # the circuitKeys as the key values
    circuit_data = {}
    for circuit_key, circuit in selected_circuits.items():
        circuit_data[circuit_key] = {}
        circuit_data[circuit_key]['circuit'] = circuit

    interface_data = get_util_interfaces(conn, plan, circuit_data)
    logging.info("Simulation analysis completed.")

    try:
        serialized_bytes = plan.serializeToBytesForVersion(PlanFormat.PlnFile, '7.5')
        with open("plan_files/plan_out.pln", "wb") as file:
            file.write(serialized_bytes)
        logging.info("Serialized plan file to bytes.")
    except Exception as err:
        logging.error("Could not save the plan file to file system!")

    return interface_data


def main():
    with open('jsongets/traffic_matrix.json', 'r') as file:
        traffic_data = json.load(file)

    selected_circuits = net.getCircuitManager().getAllCircuits()

    # Now that the circuits are chosen, create a dictionary of dictionaries using
    # the circuitKeys as the key values
    circuit_data = {}
    for circuit_key, circuit in selected_circuits.items():
        circuit_data[circuit_key] = {}
        circuit_data[circuit_key]['circuit'] = circuit

    sim_circuit_data = get_simulated_circuits(conn, plan, circuit_data)

    node_key_list = node_manager.getAllNodeKeys()

    all_nodes_circ_data = {}
    for node_key in node_key_list:
        node_name = node_key.name
        node_circ_data = {'locator': node_name.split('-')[-1]}
        node_neighbors = []
        for circ_key, circ in sim_circuit_data.items():
            if circ_key.interfaceAKey.sourceKey.name == node_name or circ_key.interfaceBKey.sourceKey.name == node_name:
                if circ_key.interfaceAKey.sourceKey.name != node_name:
                    node_neighbors.append({'hostname': circ_key.interfaceAKey.sourceKey.name, 'intf_name': 'foo'})
                elif circ_key.interfaceBKey.sourceKey.name != node_name:
                    node_neighbors.append({'hostname': circ_key.interfaceBKey.sourceKey.name, 'intf_name': 'bar'})
            node_circ_data['neighbors'] = node_neighbors

        all_nodes_circ_data[node_name] = node_circ_data

    print(json.dumps(all_nodes_circ_data, indent=2, sort_keys=True))


def new_sr_lsp(plan, src_node, dest_node, dest_sid):
    random_num = random.random()
    hop_type = SegmentListHopType.SEGMENTLISTHOPTYPE_NODE
    segment_list_hop_rec = SegmentListHopRecord(
        hopType=hop_type,
        nodeHop=NodeKey(dest_node),
        sid=int(dest_sid),
    )
    segment_list_hop_rec_list = []
    segment_list_hop_rec_list.append(segment_list_hop_rec)
    segment_list_name = f"{src_node}-{dest_node}-{dest_sid}--{random_num}"
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
    lsp_name = f"{src_node}-{dest_node}-{dest_sid}--{random_num}"
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


def get_simulated_circuits(conn, plan, circuit_data):
    '''
        Attaches simulated traffic records to circuit_data dictionary
    '''
    # To get steady state TrafficSim / UtilSim statistics, we need to build a Simulation using the RPC API
    # First, build a RouteSimulation with no FailureScenario defined.
    # Second, build TrafficSimulation using the RouteSimulation.
    # Third, use the TrafficSimuation and the list of interfaces we built earlier, to ask for Simulated
    # traffic statistics.

    sim = conn.getSimulationManager()
    r_sim = sim.newRouteSimulation(plan, FailureScenarioRecord())
    trf_sim = sim.newTrafficSimulation(r_sim, plan.getNetwork().getTrafficLevelManager().getTrafficLevel(
        TrafficLevelKey(name='Default')), None)

    for circuit in circuit_data.keys():
        # Here we are asking the API to tell us
        # how much traffic is simulated on each of side of the circuit
        simulated_traff_map = trf_sim.getInterfacesSimulatedTrafficRecords(
            [circuit.interfaceAKey, circuit.interfaceBKey])

        # Because our report is about highly utilized circuits and not interfaces, we don't care if the A size is less
        # than the B size or vice versa, so here we ignore the lesser of the two returned values.
        last_util_sim = -1
        for interface_key, int_sim_traff_record in simulated_traff_map.items():
            if int_sim_traff_record != Ice.Unset:
                if int_sim_traff_record.utilSim >= last_util_sim:
                    last_util_sim = int_sim_traff_record.utilSim
                    circuit_data[circuit]['traff_map'] = int_sim_traff_record
                    if interface_key == circuit.interfaceAKey:
                        circuit_data[circuit]['direction'] = 'A -> B'
                    else:
                        circuit_data[circuit]['direction'] = 'B -> A'
    return circuit_data


def get_util_interfaces(conn, plan, circuit_data):
    # Initialize network object
    network = plan.getNetwork()
    # Initialize sim object
    tool_mgr = conn.getToolManager()
    sim = tool_mgr.newSimAnalysis()

    print("Running new simulation...")
    sim_options = SimAnalysisOptions(
        failures=[SAFailureType.SA_FAILURETYPE_CIRCUITS]
    )
    sim.run(network, sim_options)
    interface_dict = {}
    # obtain highest wcUtil results per circuit
    for circuit in circuit_data.keys():
        intf_list = [circuit.interfaceAKey, circuit.interfaceBKey]
        for intf in intf_list:
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
                    except Exception as err:
                        try:
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name] = {
                                'worst-case-traffic': int(wc_result.wcTraffic)}
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'worst-case-util'] = round(wc_result.wcUtil,1)
                            interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                'failure-scenario'] = wc_result.failureScenario
                        except Exception as err:
                            try:
                                interface_dict[wc_result.iface.sourceKey.name] = {
                                    wc_result.iface.name: {'worst-case-traffic': int(wc_result.wcTraffic)}}
                                interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                    'worst-case-util'] = round(wc_result.wcUtil,1)
                                interface_dict[wc_result.iface.sourceKey.name][wc_result.iface.name][
                                    'failure-scenario'] = wc_result.failureScenario
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
