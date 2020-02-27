from neo4j import GraphDatabase
import os


class GraphDb:
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

    def get_driver(self):
        return self.__driver
