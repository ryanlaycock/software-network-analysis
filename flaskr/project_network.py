import network


class ProjectNetwork(network.Network):
    """Class representing a project and it's contents (Packages, classOrInterfaces and Methods in a network."""

    def __init__(self, project_name):
        # TODO Check if graph exists
        network.Network.__init__(self)
        records = self.__fetch_data(project_name)
        self.neo4j_to_network(records)

    def __fetch_data(self, project_name):
        query = ("MATCH p = (parent:Project{id:$projectName})"
                 "-[ra:Contains]->(child:Package)"
                 "-[rb:Contains]->(class:ClassOrInterface)"
                 "-[rc:Contains]->(method:Method) " + self.query_end)
        with self.db_driver.session() as session:
            result = session.run(query, parameters={"projectName": project_name})

            return result.records()
