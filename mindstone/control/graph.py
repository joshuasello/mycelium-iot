""" Graph Implementation.

"""

import warnings
from collections import Hashable, Iterable


class Node(set):
    """ Node class.

    """
    pass


class DirectedGraph(dict):
    """ Directed graph class.

    """

    def __init__(self, nodes: dict = None, edges: Iterable = None):
        super(DirectedGraph, self).__init__()
        if nodes is not None:
            for node_key, node_object in nodes.items():
                self.add_node(node_key, node_object)
        if edges is not None:
            for from_key, to_key in edges:
                self.add_edge(from_key, to_key)

    @property
    def edges(self) -> list:
        return [[from_key, to_key] for from_key, node in self.items() for to_key in node]

    @property
    def is_acyclic(self) -> bool:
        for path in self.get_all_complete_paths():
            if path[0] == path[-1]:
                return False
        return True

    def add_node(self, key: Hashable, node: set = None):
        self[key] = node if node is not None else Node()

    def remove_node(self, key: Hashable):
        if key in self:
            del self[key]

    def add_edge(self, from_key: Hashable, to_key: Hashable):
        if from_key == to_key:
            raise ValueError("A noe cannot be connected to itself")
        self[from_key].add(to_key)

    def remove_edge(self, from_key: Hashable, to_key: Hashable):
        self[from_key].remove(to_key)

    def add_nodes_from_iterable(self, iterable: Iterable):
        for node_definition in iterable:
            self.add_node(*node_definition)

    def add_edges_from_iterable(self, iterable: Iterable):
        for edge_definition in iterable:
            self.add_edge(*edge_definition)

    def get_complete_paths(self, key: Hashable, sort: bool = False) -> list:
        paths = []
        self._get_paths_util(key, paths, [])
        return sorted(paths, key=lambda x: len(x)) if sort else paths

    def get_all_complete_paths(self) -> list:
        paths = []
        for key in self.keys():
            paths += self.get_complete_paths(key)
        return paths

    def in_neighbors(self, key: Hashable) -> set:
        return set([k for k, n in self.items() if key in n])

    def out_neighbors(self, key: Hashable) -> set:
        return set(self[key])

    def in_degree(self, key: Hashable) -> int:
        return len(self.in_neighbors(key))

    def out_degree(self, key: Hashable) -> int:
        return len(self.out_neighbors(key))

    def isolated(self) -> set:
        isolated_nodes = set()
        for key in self.keys():
            if self.in_degree(key) == self.out_degree(key) == 0:
                isolated_nodes.add(key)
        return isolated_nodes

    def is_isolated(self, key: Hashable) -> bool:
        return key in self.isolated()

    def is_source(self, key: Hashable) -> bool:
        return self.in_degree(key) == 0

    def is_sink(self, key: Hashable) -> bool:
        return self.out_degree(key) == 0

    def merge(self, to_merge, new_edges: Iterable = None):
        # 1. make sure that the graph is formatted correctly to be merged
        if not isinstance(to_merge, DirectedGraph):
            raise TypeError("Object to append must be a network.")
        if not self.keys().isdisjoint(to_merge.keys()):
            warnings.warn("There are some key naming conflicts between the two networks.")
        # 2. combine the two graph's nodes
        self.update(to_merge)
        # 3. add any additional communication if implemented
        if new_edges is not None:
            self.add_nodes_from_iterable(new_edges)

    def _get_paths_util(self, key: Hashable, paths: list, prepended: list, start: Hashable = None):
        prepended += [key]
        out_neighbors = self.out_neighbors(key)
        if not out_neighbors or key == start:
            return prepended
        start = key if start is None else start
        for child in out_neighbors:
            new_path = self._get_paths_util(child, paths, list(prepended), start)
            if new_path:
                paths.append(new_path)
