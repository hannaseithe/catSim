from dataclasses import dataclass, field
from typing import Optional
import networkx as nx


@dataclass
class CatMetrics:
    percent_time_spent_home: float
    percent_time_spent_on_edge: float
    percent_time_spent_on_neutral_ground: float
    percent_time_spent_at_friends_house: float
    average_iter_spent_at_home: float
    average_iter_spent_at_friends_home: float
    average_iter_spent_on_neutral_node: float
    amount_of_cats_interacted_with: int
    amount_of_friends: int
    amount_of_enemies: int
    percent_time_spent_fighting: float
    percent_time_spent_friendly_interaction: float
    percent_time_spent_sleeping: float
    amount_friendgroups: int
    average_size_friendgroup: float


@dataclass
class RelationshipMetrics:
    stability: float



@dataclass(frozen=True)
class CatTraits:
    id: int
    name: str
    home: int
    aggressive: float
    lazy:float

@dataclass
class CatStats:
    iter_at_home: int = 0
    iter_on_edge: int = 0
    iter_at_friendly: int = 0
    iter_at_neutral: int = 0
    fights: int = 0
    friendly_interaction: int = 0
    sleeps: int = 0
    times_at_home: float = 0
    times_at_friendly: float = 0
    times_at_neutral: float = 0
    interacted_with: set = field(default_factory=set)


class Cat:
    def __init__(self, traits: CatTraits):
        self.traits = traits
        self.current_node = traits.home
        self.target_node: Optional[int] = None
        self.needs_to_run = False
        self.time_at_current_node = 0

        self.stats: CatStats = CatStats()
        self.metrics: Optional[CatMetrics] = None
    
    def __str__(self):
        if self.current_node is not None:
            return f"{self.traits.name} (n: #{self.current_node})"
        else: return f"{self.traits.name} -> n #{self.target_node}"
    
    def __repr__(self):
        if self.current_node is not None:
            return f"{self.traits.name} at node #{self.current_node}"
        else: return f"{self.traits.name} moving to node #{self.target_node}"

    def leave(self, target_node):
        if self.current_node == target_node:
            raise ValueError('A cat cannot leave for the same node the cat is already at')
        self.current_node=None
        self.target_node = target_node

    def arrive(self):
        self.current_node =self.target_node
        self.target_node = None

    def is_on_the_edge(self):
        return self.current_node is None
    
    def is_at_home(self):
        return self.current_node == self.traits.home
    

@dataclass(frozen=True)
class Edge:
    node1: int
    node2: int

    def node_in_edge(self,node_id):
        return node_id == self.node1 or node_id == self.node2
    
    def other_node(self,node_id):
        return self.node1 if self.node2 == node_id else self.node2

@dataclass(frozen=True)
class Node:
    id: int
    number_of_edges: int



@dataclass(frozen=True)
class RelationshipTraits:
    cat1: int
    cat2: int

@dataclass
class RelationshipStats:
    absolute_delta:float = 0

class Relationship:
    def __init__(self,traits:RelationshipTraits):
        self.traits = traits
        self.value = 0
        self.stats = RelationshipStats()
        self.metrics: Optional[RelationshipMetrics] = None

    def __str__(self):
        return f"Relationship: Cat {self.traits.cat1} - Cat {self.traits.cat2}"
    
    def __repr__(self):
        return f"Relationship between Cat {self.traits.cat1} and Cat {self.traits.cat2} - value: {self.value}"
    
    def other_cat(self,cat1):
        return self.traits.cat1 if cat1 == self.traits.cat2 else self.traits.cat2

    def is_relationship(self,cat1,cat2):
        return (self.traits.cat1 == cat1 and self.traits.cat2 ==cat2) or (self.traits.cat1 == cat2 and self.traits.cat2 ==cat1)

