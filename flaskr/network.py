import networkx as nx
import graph_db


class Network:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.db = graph_db.GraphDb()
        self.db_driver = self.db.get_driver()
        self.query_end = ("UNWIND nodes(p) as allnodes WITH COLLECT(ID(allnodes)) AS ALLID "
                          "MATCH (a)-[r2]-(b) "
                          "WHERE ID(a) IN ALLID AND ID(b) IN ALLID "
                          "WITH DISTINCT r2 "
                          "RETURN startNode(r2), type(r2), endNode(r2)")

    def project_exists(self):
        return self.graph is not None

    def get_network_json(self):
        """Parse the network into the standard JSON structure for most graphs libraries."""
        graph_data = nx.node_link_data(self.graph)
        return graph_data

    def neo4j_to_network(self, records):
        """Takes a neo4j result.records and generates a networkx network into self.graph"""
        for record in records:
            self.__add_node(record[0])  # Add parent/source node
            self.__add_node(record[2])  # Add child/target node
            self.__add_edge(record[0], record[1], record[2])  # Add edge

    def __add_node(self, node):
        node_id = node.id
        node_type = list(node.labels)[0]
        # TODO Add Artifact & Attribute
        if node_type == "Project":
            self.graph.add_node(node_id, id=node["id"], name=node["id"], type=node_type)
        elif node_type == "Package" or node_type == "ClassOrInterface" or node_type == "Method":
            self.graph.add_node(node_id, id=node["id"], name=node["name"], type=node_type)

    def __add_edge(self, source_node, relation_type, target_node):
        self.graph.add_edge(source_node.id, target_node.id, type=relation_type)