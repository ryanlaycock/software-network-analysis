import network
import networkx as nx
import main


class ProjectNetwork(network.Network):
    """Class representing a project and it's contents (Packages, classOrInterfaces and Methods in a network."""

    def __init__(self, project_name):
        # TODO Check if graph exists
        network.Network.__init__(self)
        records = self.__fetch_data(project_name)
        self.neo4j_to_network(records)

    def __fetch_data(self, project_name):
        print("Fetching data for", project_name)
        query = ("MATCH p = (parent:Project{id:$projectName})"
                 "-[ra:Contains]->(child:Package)"
                 "-[rb:Contains]->(class:ClassOrInterface)"
                 "-[rc:Contains]->(method:Method) " + self.query_end)
        with self.db_driver.session() as session:
            result = session.run(query, parameters={"projectName": project_name})
            return result.records()

    def compute_metrics(self, project_name):
        node_metrics = {}  # {a:{comp_a:x, comp_b:y}}
        project_node = ""
        for node in self.graph.nodes(data=True):
            if node[1]['type'] == "Project":
                project_node = node
                break
        if project_node == "":
            print("Project node not found")
            return
        project_child_nodes = nx.ego_graph(self.graph, project_node[0])
        reversed_graph = self.graph.reverse()  # For nWeakComp
        project_comp = 0
        for project_child_node in project_child_nodes:  # For each package
            package_comp = 0
            if self.graph.nodes[project_child_node]["type"] != "Package":
                continue
            print("Analysing metrics for package:", self.graph.nodes[project_child_node]["id"])
            package_child_nodes = nx.ego_graph(self.graph, project_child_node)
            for package_child_node in package_child_nodes:  # For each class
                if self.graph.nodes[package_child_node]["type"] != "ClassOrInterface":
                    continue
                print("Analysing metrics for class:", self.graph.nodes[package_child_node]["id"])
                class_comp = 0
                class_child_nodes = nx.ego_graph(self.graph, package_child_node)
                for class_child_node in class_child_nodes:  # For each method
                    if self.graph.nodes[class_child_node]["type"] == "Method":
                        node_metrics[class_child_node] = self.get_node_base_metrics(class_child_node, reversed_graph)
                        procedure_comp = self.procedure_complexity(self.graph.in_degree(class_child_node),
                                                                   self.graph.out_degree(class_child_node))
                        node_metrics[class_child_node]["procedureComplexity"] = round(procedure_comp, 8)
                        class_comp += procedure_comp
                node_metrics[package_child_node] = self.get_node_base_metrics(package_child_node, reversed_graph)
                node_metrics[package_child_node]["classComplexity"] = round(class_comp, 8)
                package_comp += class_comp

            node_metrics[project_child_node] = self.get_node_base_metrics(project_child_node, reversed_graph)
            node_metrics[project_child_node]["packageComp"] = round(package_comp, 8)
            project_comp += package_comp
        node_metrics[project_node[0]] = self.get_node_base_metrics(project_node[0], reversed_graph)
        node_metrics[project_node[0]]["projectComp"] = round(project_comp, 8)
        node_metrics[project_node[0]]["avgCodeChangePerWeek"] = round(main.compute_avg_code_change(project_name), 8)
        node_metrics[project_node[0]]["avgCommitsPerWeek"] = round(main.compute_avg_commit_count(project_name), 8)
        self.add_metrics_to_nodes(node_metrics)
        print("Metrics analysed")

        return node_metrics

    def get_node_base_metrics(self, node, reversed_graph):
        degree_in = self.graph.in_degree(node)
        degree_out = self.graph.out_degree(node)
        n_weak_comp = self.n_weak_comp(node, reversed_graph)
        n_uncon_weak_comp = n_weak_comp["unconnected"]
        n_con_weak_comp = n_weak_comp["connected"]
        modularity = round(self.modularity(nx.ego_graph(self.graph, node, undirected=True)), 8)
        if modularity == 0:
            modularity = 0.1
        network_comp = round((degree_out + 2 * n_uncon_weak_comp) / modularity, 8)
        return {
            "networkComp": network_comp,
            "degreeIn": degree_in,
            "degreeOut": degree_out,
            "nUnconWeakComp": n_uncon_weak_comp,
            "nConWeakComp": n_con_weak_comp,
            "modularity": modularity,
        }

    def get_internal_metrics(self):
        metrics = []
        nodes = self.graph.nodes(data=True)
        reversed_graph = self.graph.reverse()  # For nWeakComp
        for node in nodes:
            if node[1]['type'] == "Project":
                continue
            n_weak_comp = self.n_weak_comp(node[0], reversed_graph)
            metrics.append({
                "internalId": node[0],
                "id": node[1]['id'],
                "type": node[1]['type'],
                "name": node[1]['name'],
                "degreeOut": self.graph.out_degree(node[0]),
                "degreeIn": self.graph.in_degree(node[0]),
                "procedureComplexity": self.procedure_complexity(self.graph.in_degree(node[0]),
                                                                 self.graph.out_degree(node[0])),
                "nUnconnectedWeakComp": n_weak_comp["unconnected"],
                "nConnectedWeakComp": n_weak_comp["connected"],
            })
        return metrics
