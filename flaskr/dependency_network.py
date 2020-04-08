import network


class DependencyNetwork(network.Network):
    """Class representing a project and it's dependencies."""

    def __init__(self, project_name):
        # TODO Check if graph exists
        network.Network.__init__(self)
        records = self.__fetch_data(project_name)
        self.neo4j_to_network(records)

    def __fetch_data(self, project_name):
        print("Fetching dependencies for", project_name)
        # query = ("MATCH p = (parent:Project{id:$projectName})"
        #          "-[:Depends*0..1]-(child:Project) " + self.query_end)
        query = ("MATCH p = (parent:Project{id:$projectName})"
                 "-[ra:Contains]->(child:Artifact)"
                 "-[rb:Depends]->(dep:Artifact)" + self.query_end)

        with self.db_driver.session() as session:
            result = session.run(query, parameters={"projectName": project_name})
            return result.records()

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
                "nUnconnectedWeakComp": n_weak_comp["unconnected"],
                "nConnectedWeakComp": n_weak_comp["connected"],
            })
        return metrics
