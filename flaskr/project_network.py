import networkx as nx
import os


class ProjectNetwork():
    def __init__(self, project_graph):
        self.__debug = os.getenv("DEBUG")
        self.graph = nx.DiGraph()
        self.__neo4j_to_network(project_graph)

    def get_network_json(self):
        """Parse the network into the standard JSON structure for most graphs libraries."""
        graph_data = nx.node_link_data(self.graph)

        for node in graph_data.get('nodes'):
            node['name'] = (self.graph.nodes[node.get('id')].get('id'))  # Add id to node data as 'name'

        return graph_data

    def __neo4j_to_network(self, records):
        """Takes a neo4j result.records and generates a networkx network into self.graph"""
        for record in records:
            # labels = record[0].labels
            self.__add_node(record[0].id, record[0].get("id"))  # Add first node
            self.__add_node(record[1].id, record[1].get("id"))  # Add second node
            self.__add_edge(record[0].id, record[1].id)  # Add edge

    def __add_node(self, neo4j_id, node_id):
        """Adds a node to self.graph"""
        if self.graph.has_node(neo4j_id):  # Node already in graph
            print("Node " + node_id + " already in graph.")
            return False
        else:
            self.graph.add_node(neo4j_id, id=node_id, type="project")
            if self.__debug:
                print("Added " + node_id + " to graph.")
            return True

    def __add_edge(self, node_a_id, node_b_id):
        """Adds an edge to self.graph"""
        if not self.graph.has_edge(node_a_id, node_b_id):
            self.graph.add_edge(node_a_id, node_b_id, type="depends")
            if self.__debug:
                print("Added edge", node_a_id, "to", node_b_id, "to graph.")
            return True
        if self.__debug:
            print("Edge", node_a_id, "to", node_b_id, "already in graph.")
        return False
