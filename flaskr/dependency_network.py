import network
import networkx as nx
import time
from collections import Counter


class DependencyNetwork(network.Network):
    """Class representing a project and it's dependencies."""

    def __init__(self,):
        # TODO Check if graph exists
        network.Network.__init__(self)
        start = time.time()
        records = self.__fetch_data()
        self.neo4j_to_network_artifact(records)
        print("Fetched data and built graph. Took:", time.time() - start, "seconds.")
        start = time.time()
        self.__page_rank = nx.pagerank(self.graph)
        print("Calculated pagerank. Took:", time.time() - start, "seconds.")
        start = time.time()
        self.__eigenvector = nx.eigenvector_centrality_numpy(self.graph)
        print("Calculated eigenvector. Took:", time.time() - start, "seconds.")
        start = time.time()
        self.__dependent_closeness = nx.closeness_centrality(self.graph)
        self.__dependency_closeness = nx.closeness_centrality(self.graph.reverse())
        print(self.__dependent_closeness)
        print(self.__dependency_closeness)
        print("Calculated eigenvector. Took:", time.time() - start, "seconds.")

    def __fetch_data(self):
        print("Fetching dependencies.")
        # query = ("MATCH p = (parent:Project{id:$projectName})"
        #          "-[:Contains]->(child:Artifact)"
        #          "<-[:Depends*0..2]-(dep:Artifact)" + self.query_end)

        # Dependencies ?
        # query = ("MATCH p = (parent:Project{id:$projectName})"
        #          "-[:Contains]->(child:Artifact)"
        #          "-[:Depends*0..3]->(dep:Artifact)" + self.query_end)

        # Dependent projects
        # query = ("MATCH p = (parent:Project{id:$projectName})"
        #          "-[:Contains]->(child:Artifact)"
        #          "<-[:Depends]-(dep:Artifact)"
        #          "<-[:Contains]-(:Project) " + self.query_end)
        # with self.db_driver.session() as session:
        #     result = session.run(query, parameters={"projectName": project_name})
        #     return result.records()

        # All artifacts
        query = ("MATCH p=(:Artifact)"
                 "UNWIND nodes(p) as allnodes WITH COLLECT(ID(allnodes)) AS ALLID "
                 "MATCH (a)-[r2]-(b) "
                 "WHERE ID(a) IN ALLID AND ID(b) IN ALLID "
                 "WITH DISTINCT r2 "
                 "RETURN id(startNode(r2)), type(r2), id(endNode(r2))")
        with self.db_driver.session() as session:
            result = session.run(query)
            return result.records()

    def neo4j_to_network_artifact(self, records):
        """Takes a neo4j result.records and generates a networkx network into self.graph"""
        for record in records:
            self.__add_node_artifact(record[0])  # Add parent/source node
            self.__add_node_artifact(record[2])  # Add child/target node
            self.__add_edge_artifact(record[0], record[1], record[2])  # Add edge

    def __add_node_artifact(self, node):
        self.graph.add_node(node)

    def __add_edge_artifact(self, source_node, relation_type, target_node):
        self.graph.add_edge(source_node, target_node, type=relation_type)

    # def compute_similarity(self, source_id):
    #     ego = nx.ego_graph(self.graph, source_id, radius=1, center=True, undirected=True)
    #     print(ego.number_of_nodes())
    #     sim = nx.simrank_similarity(ego, self.graph.nodes[source_id])
    #     return sim

    def get_closeness_dependent(self, artifact_id):
        if self.__dependent_closeness.__contains__(artifact_id):
            return self.__dependent_closeness[artifact_id]
        else:
            return 0

    def get_closeness_dependency(self, artifact_id):
        if self.__dependency_closeness.__contains__(artifact_id):
            return self.__dependency_closeness[artifact_id]
        else:
            return 0

    def get_pagerank(self, artifact_id):
        k = Counter(self.__page_rank)
        max = k.most_common(1)[0][0]
        if self.__page_rank.__contains__(artifact_id):
            pr = self.__page_rank[artifact_id]
            return pr
            # return (pr / max) * 100
        else:
            return 0

    def get_eigenvector(self, artifact_id):
        k = Counter(self.__eigenvector)
        max = k.most_common(1)[0][0]
        if self.__eigenvector.__contains__(artifact_id):
            ev = self.__eigenvector[artifact_id]
            return ev
            # return (ev/max)*100
        else:
            return 0
        # TODO Key index error catch - node may easily not be in here

    # def get_internal_metrics(self):
    #     metrics = []
    #     nodes = self.graph.nodes(data=True)
    #     reversed_graph = self.graph.reverse()  # For nWeakComp
    #     for node in nodes:
    #         if node[1]['type'] == "Project":
    #             continue
    #         n_weak_comp = self.n_weak_comp(node[0], reversed_graph)
    #         metrics.append({
    #             "internalId": node[0],
    #             "id": node[1]['id'],
    #             "type": node[1]['type'],
    #             "name": node[1]['name'],
    #             "degreeOut": self.graph.out_degree(node[0]),
    #             "degreeIn": self.graph.in_degree(node[0]),
    #             "nUnconnectedWeakComp": n_weak_comp["unconnected"],
    #             "nConnectedWeakComp": n_weak_comp["connected"],
    #         })
    #     return metric

    def compute_dependents(self, project_node):
        projects = []
        nodes = nx.get_node_attributes(self.graph, 'type')
        for node_id, node_type in nodes.items():
            if node_type == 'Project':
                projects.append(self.graph.nodes[node_id])
        return projects

    def compute_artifact_metrics(self, artifact_id):
        if not self.graph.has_node(artifact_id):
            # TODO Change this
            return {
                "artifactComplexity": 0,
                "dependent_count": 0,
                "nUnconWeakComp": 0,
                "nConWeakComp": 0,
                "modularity": 0,
            }
        dependent_graph = self.graph.subgraph(nx.dfs_preorder_nodes(self.graph, source=artifact_id))
        dependent_count = dependent_graph.number_of_nodes() - 1
        print(dependent_count)
        if dependent_count == 0:
            return {
                "artifactComplexity": 0,
                "dependent_count": 0,
                "nUnconWeakComp": 0,
                "nConWeakComp": 0,
                "modularity": 0,
            }
        metrics = {}
        sub = nx.ego_graph(dependent_graph.reverse(), artifact_id, center=False)  # Get the in ego network
        unconnected = 0
        connected = 0
        for c in sorted(nx.weakly_connected_components(sub), key=len, reverse=True):
            if len(c) == 1:
                unconnected += 1
            else:
                connected += 1
        modularity = self.modularity(dependent_graph)
        if modularity == 0:
            modularity = 0.000001
        artifact_complexity = dependent_count / modularity
        return {
            "artifactComplexity": artifact_complexity,
            "dependent_count": dependent_count,
            "nUnconWeakComp": unconnected,
            "nConWeakComp": connected,
            "modularity": modularity,
        }

    def compute_metrics(self, project_node):
        project_artifacts = nx.ego_graph(self.graph, project_node[0])
        # Graph of all artifacts, without the project node (all relations should be "Depends")
        graph_of_artifacts_only = nx.ego_graph(self.graph, project_node[0], center=False, undirected=True, radius=100)
        node_metrics = {}
        node_types = {}
        page_rank = nx.pagerank(graph_of_artifacts_only)
        eigenvector_centrality = nx.eigenvector_centrality_numpy(graph_of_artifacts_only)
        reversed_graph = self.graph.reverse()
        for project_artifact in project_artifacts:
            if self.graph.nodes[project_artifact]["type"] == "Artifact":
                print("Analysing metrics for project artifact:", self.graph.nodes[project_artifact]["artifact"])
                node_metrics[project_artifact] = self.get_node_base_metrics(project_artifact, reversed_graph)
                node_metrics[project_artifact]["pageRank"] = round(page_rank[project_artifact], 8)
                node_metrics[project_artifact]["eigenvectorCentrality"] = round(
                    eigenvector_centrality[project_artifact], 8)
                self.add_metrics_to_nodes({project_artifact: node_metrics[project_artifact]})
                node_types[project_artifact] = "Artifact"
                artifact_comp = 0
                # Artifact dependencies
                artifact_deps = nx.ego_graph(self.graph,
                                             project_artifact)  # Outgoing nodes from artifact (dependencies)
                for artifact_dep in artifact_deps:
                    if self.graph.nodes[artifact_dep]["type"] == "Artifact" and artifact_dep not in node_types:
                        print("Analysing metrics for project dependency:", self.graph.nodes[artifact_dep]["artifact"])
                        node_metrics[artifact_dep] = self.get_node_base_metrics(artifact_dep, reversed_graph)
                        node_metrics[artifact_dep]["pageRank"] = round(page_rank[artifact_dep], 8)
                        node_metrics[artifact_dep]["eigenvectorCentrality"] = round(
                            eigenvector_centrality[artifact_dep], 8)
                        node_types[artifact_dep] = "DirectDependency"

                        # TEST STUFF
                        # dep_complexity = ((self.graph.out_degree(artifact_dep)+1)*(self.graph.in_degree(artifact_dep)+1))**2
                    artifact_comp += node_metrics[artifact_dep]["nUnconWeakComp"]

                node_metrics[project_artifact]["nUnconWeakComp"] = artifact_comp

                # Artifact dependents
                artifact_dependents = nx.ego_graph(reversed_graph,
                                                   project_artifact)  # Incoming nodes into artifact (dependents)
                for artifact_dependent in artifact_dependents:
                    if self.graph.nodes[artifact_dependent][
                        "type"] == "Artifact" and artifact_dependent != project_artifact:
                        print("Analysing metrics for project dependence:",
                              self.graph.nodes[artifact_dependent]["artifact"])
                        # If node is dependency and dependent don't reanalyze metrics, but add to dependents list
                        if artifact_dependent not in node_metrics:
                            node_metrics[artifact_dependent] = self.get_node_base_metrics(artifact_dependent,
                                                                                          reversed_graph)
                            node_metrics[artifact_dependent]["pageRank"] = round(page_rank[artifact_dependent], 8)
                            node_metrics[artifact_dependent]["eigenvectorCentrality"] = round(
                                eigenvector_centrality[artifact_dependent], 8)
                            node_types[artifact_dependent] = "DirectDependent"
                        else:
                            node_types[artifact_dependent] = "DirectDependentAndDependency"
        return {"node_metrics": node_metrics, "node_types": node_types}
