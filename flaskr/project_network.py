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
                 "-[rc:Contains]->(method:Method)"
                 "-[rd:Calls*0..1]->(depMethod:Method) " + self.query_end)
        with self.db_driver.session() as session:
            result = session.run(query, parameters={"projectName": project_name})
            return result.records()

    def compute_metrics(self, project_name, project_node):
        node_metrics = {}  # {a:{comp_a:x, comp_b:y}}
        project_child_nodes = nx.ego_graph(self.graph, project_node[0])
        total = nx.number_of_nodes(self.graph)
        reversed_graph = self.graph.reverse()  # For nWeakComp
        project_network_comp = 0
        project_procedure_comp = 0
        progress = 0
        for project_child_node in project_child_nodes:  # For each package
            package_network_comp = 0
            if self.graph.nodes[project_child_node]["type"] != "Package":
                continue
            print("Analysing metrics for package:", self.graph.nodes[project_child_node]["id"])
            main.post_status_update(project_name, "in_progress",
                                    "Analysing metrics for package:" + self.graph.nodes[project_child_node]["id"]
                                    + ". Component " + str(progress) + " of " + str(total) + ".")
            package_child_nodes = nx.ego_graph(self.graph, project_child_node)
            for package_child_node in package_child_nodes:  # For each class
                if self.graph.nodes[package_child_node]["type"] != "ClassOrInterface":
                    continue
                print("Analysing metrics for class:", self.graph.nodes[package_child_node]["id"])
                main.post_status_update(project_name, "in_progress",
                                        "Analysing metrics for class:" + self.graph.nodes[package_child_node]["id"]
                                        + ". Component " + str(progress) + " of " + str(total) + ".")
                class_network_comp = 0
                class_child_nodes = nx.ego_graph(self.graph, package_child_node)
                for class_child_node in class_child_nodes:  # For each method
                    if self.graph.nodes[class_child_node]["type"] == "Method":
                        progress += 1
                        node_metrics[class_child_node] = {}
                        method_network_comp = self.get_network_comp(class_child_node, reversed_graph)
                        procedure_comp = self.procedure_complexity(self.graph.in_degree(class_child_node),
                                                                   self.graph.out_degree(class_child_node))
                        node_metrics[class_child_node]["network_comp"] = method_network_comp
                        node_metrics[class_child_node]["procedure_comp"] = procedure_comp
                        project_procedure_comp += procedure_comp
                        class_network_comp += method_network_comp
                node_metrics[package_child_node] = {}
                node_metrics[package_child_node]["network_comp"] = class_network_comp
                package_network_comp += class_network_comp

            node_metrics[project_child_node] = {}
            node_metrics[project_child_node]["network_comp"] = package_network_comp
            project_network_comp += package_network_comp

        node_metrics[project_node[0]] = {}
        node_metrics[project_node[0]]["code_churn"] = round(main.compute_avg_code_change(project_name), 8)
        node_metrics[project_node[0]]["network_comp"] = project_network_comp
        node_metrics[project_node[0]]["procedure_comp"] = project_procedure_comp

        main.post_status_update(project_name, "in_progress", "Project analysed, saving for next time.")
        self.add_metrics_to_nodes(node_metrics)
        print("Internal metrics analysed.")

        return node_metrics
