import networkx as nx
import graph_db
from networkx.algorithms.community import greedy_modularity_communities, quality


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

    def get_stats(self):
        num_of_nodes = self.graph.number_of_nodes()
        num_of_edges = self.graph.number_of_edges()
        num_of_node_types = self.__get_node_count_of_types()
        num_of_edge_types = self.__get_edge_count_of_types()
        return {
            'num_of_nodes': num_of_nodes,
            'num_of_edges': num_of_edges,
            'num_of_node_types': num_of_node_types,
            'num_of_edge_types': num_of_edge_types
        }

    def get_scc(self):
        scc = []
        for c in sorted(nx.strongly_connected_components(self.graph), key=len, reverse=True):
            if len(c) > 1:
                scc.append(nx.node_link_data(self.graph.subgraph(c).copy()))
        return scc

    def get_degree(self, limit, graphs):
        nodes = nx.degree_centrality(self.graph)
        sorted_nodes = sorted(((value, key) for (key, value) in nodes.items()), reverse=True)
        if not limit == 0:
            sorted_nodes = sorted_nodes[:limit]
        format_nodes = []
        for node in sorted_nodes:
            sub = nx.ego_graph(self.graph, node[1], undirected=True)
            if graphs:
                format_nodes.append({
                    'id': node[1],
                    'degree': node[0],
                    'node': self.graph.nodes[node[1]],
                    'subgraph': nx.node_link_data(sub)
                })
            else:
                format_nodes.append({
                    'id': node[1],
                    'degree': node[0],
                    'node': self.graph.nodes[node[1]],
                })

        return format_nodes

    def procedure_complexity(self, fan_in, fan_out):
        return (fan_in * fan_out) ** 2

    def modularity(self, graph):
        communities = greedy_modularity_communities(nx.Graph(graph))
        modularity = quality.modularity(graph, communities)

        return modularity

    def n_weak_comp(self, node, reversed_graph):
        sub = nx.ego_graph(reversed_graph, node, radius=1, center=False)  # Get the in ego network
        unconnected = 0
        connected = 0
        for c in sorted(nx.weakly_connected_components(sub), key=len, reverse=True):
            if len(c) == 1:
                unconnected += 1
            else:
                connected += 1
        return {"connected": connected, "unconnected": unconnected}

    def __get_node_count_of_types(self):
        count = {}
        nodes = nx.get_node_attributes(self.graph, 'type')
        for node_id, node_type in nodes.items():
            if node_type not in count.keys():
                count[node_type] = 1
            else:
                count[node_type] += 1
        return count

    def __get_edge_count_of_types(self):
        count = {}
        edges = nx.get_edge_attributes(self.graph, 'type')
        for edge_id, edge_type in edges.items():
            if edge_type not in count.keys():
                count[edge_type] = 1
            else:
                count[edge_type] += 1
        return count

    def project_exists(self):
        return self.graph is not None

    def is_empty(self):
        return nx.is_empty(self.graph)

    def get_network_json(self):
        """Parse the network into the standard JSON structure for most graphs libraries."""
        graph_data = nx.node_link_data(self.graph)
        return graph_data

    def get_component_network_json(self, component):
        """Parse the network into the standard JSON structure for most graphs libraries."""
        sub = nx.ego_graph(self.graph, int(component), undirected=True)
        graph_data = nx.node_link_data(sub)
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
        if node_type == "Project" or node_type == "Artifact":
            self.graph.add_node(node_id, id=node["id"], name=node["id"], type=node_type)
        elif node_type == "Attribute":
            return  # Don't care about attributes
        else:
            self.graph.add_node(node_id, id=node["id"], name=node["name"], type=node_type)

    def __add_edge(self, source_node, relation_type, target_node):
        self.graph.add_edge(source_node.id, target_node.id, type=relation_type)

    def add_metrics_to_nodes(self, node_metrics):
        with self.db_driver.session() as session:
            for node_id, metric in node_metrics.items():
                print("Adding metrics to node id:", node_id)
                session.write_transaction(self.__metrics_to_node_tx, node_id, metric)

    def __metrics_to_node_tx(self, tx, node_id, metrics):
        properties = ",".join('{0}:{1}'.format(key, val) for key, val in metrics.items())
        transaction = ("MATCH (n) WHERE id(n)=" + str(node_id) +
                       " SET n += {" + properties + "}")
        return tx.run(transaction)
