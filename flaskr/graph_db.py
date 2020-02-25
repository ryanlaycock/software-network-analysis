from neo4j import GraphDatabase
import os


class GraphDb:
    # Get environment variables

    def __init__(self):
        self.__neo4j_user = os.getenv("NEO4J_USER")
        self.__neo4j_pass = os.getenv("NEO4J_PASS")
        self.__neo4j_addr = os.getenv("NEO4J_ADDR")

        self.__driver = GraphDatabase.driver(
            self.__neo4j_addr,
            auth=(
                self.__neo4j_user,
                self.__neo4j_pass
            ),
            encrypted=False)

    def get_graph_project(self, project_name):
        """
        Get the graph data of a Project and all of the projects children (pockages, methods, etc).

        Return: result.records of the neo4j call
        """
        query = ("MATCH (project:Project {id:$projectName})"
                 "-[:Contains]->(package:Package)"
                 "-[:Contains]->(class:ClassOrInterface)"
                 "-[:Contains]->(method:Method)"
                 "RETURN project,package,class,method")

        with self.__driver.session() as session:
            result = session.run(query, parameters={"projectName": project_name})
            # result = session.read_transaction(query)
            return result.records()
