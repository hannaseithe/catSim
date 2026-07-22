from __future__ import annotations
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import List, Optional

from simulations.cat_sim_1.utils import validate_dict


@dataclass
class CatMetrics:
    percent_time_spent_home: float
    percent_time_spent_on_edge: float
    percent_time_spent_on_neutral_ground: float
    percent_time_spent_at_friends_house: float
    average_iter_spent_at_home: float
    average_iter_spent_at_friends_home: float
    average_iter_spent_on_neutral_node: float
    percent_of_cats_interacted_with: float
    percent_of_friends: float
    percent_of_enemies: float
    percent_of_aquaintances: float
    percent_time_spent_fighting: float
    percent_time_spent_friendly_interaction: float
    percent_time_spent_sleeping: float
    amount_friendgroups: int
    average_size_friendgroup: float
    exploration_index: float
    relationship_entropy: float

    @classmethod
    def from_dict(cls, data: dict) -> CatMetrics:
        validate_dict(data, cls)
        return CatMetrics(**data)


@dataclass
class RelationshipMetrics:
    stability: float
    volatility: float
    min_value: float
    max_value: float
    number_of_sign_flips: int

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipMetrics:
        validate_dict(data, cls)
        return RelationshipMetrics(**data)

class TraitType(Enum):
    AGGRESSION = "aggression"
    CONFIDENCE = "confidence"
    CURIOSITY = "curiosity"
    ACTIVENESS = "activeness"
    STRENGTH = "strength"

@dataclass(frozen=True)
class CatTraits:
    aggression: float
    confidence: float
    curiosity: float
    activeness: float
    strength: float 

    @classmethod
    def from_dict(cls, data: dict) -> CatTraits:
        validate_dict(data, cls)
        return CatTraits(**data)
    
assert {f.name for f in fields(CatTraits)} == {
    need.value for need in TraitType
}, "TraitType and CatTraits fields are out of sync."

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
    nodes_visited: set = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: dict) -> CatStats:
        validate_dict(data, cls)
        return CatStats(
            interacted_with=set(data['interacted_with']),
            nodes_visited=set(data['nodes_visited']),
            **{k:v for k,v in data.items() if k not in ('interacted_with', 'nodes_visited')}
            )

class NeedType(Enum):
    HEALTH = "health"
    FOOD = "food"
    TOILET = "toilet"
    ENERGY = "energy"
    SOCIAL = "social"
    HUNT = "hunt"
    EXPLORATION = "exploration"
    TERRITORY = "territory"
    HYGIENE = "hygiene"

@dataclass
class CatNeeds:
    health: float
    food: float
    toilet: float
    energy: float
    social: float
    hunt: float
    exploration: float
    territory: float
    hygiene: float

    @classmethod
    def from_dict(cls, data: dict) -> CatNeeds:
        validate_dict(data, cls)
        return CatNeeds(**data)
    
assert {f.name for f in fields(CatNeeds)} == {
    need.value for need in NeedType
}, "NeedType and CatNeeds fields are out of sync."

@dataclass
class MemoryNode:
    novelty_score: float
    last_seen_cats: List[int]

    @classmethod
    def from_dict(cls, data: dict) -> MemoryNode:
        validate_dict(data,cls)
        return MemoryNode(**data)


@dataclass
class CatMemory:
    visited_nodes: dict[int, MemoryNode]
    
    @classmethod
    def from_dict(cls, data: dict) -> CatMemory:
        return CatMemory(
            visited_nodes={
                int(k): MemoryNode(**v) for k, v in data["visited_nodes"].items()
            }
        )


@dataclass(eq=False)
class Cat:    
    id: int
    name: str
    home: int
    traits: CatTraits
    needs: CatNeeds
    incapacitated_until: Optional[int]
    memory: CatMemory
    current_node: int
    time_at_current_node:int = 0
    will_move_to: Optional[int] = None
    stats: CatStats = field(default_factory=CatStats)
    metrics: Optional[CatMetrics] = None

    def __post_init__(self):
        if self.current_node is None:
            self.current_node = self.traits.home
        if len(self.stats.nodes_visited) == 0:
            self.stats.nodes_visited.add(self.traits.home)

    def __str__(self):
        if self.current_node is not None:
            return f"{self.traits.name} (n: #{self.current_node})"
        else:
            return f"{self.traits.name} -> n #{self.target_node}"

    def __repr__(self):
        if self.current_node is not None:
            return f"{self.traits.name} at node #{self.current_node}"
        else:
            return f"{self.traits.name} moving to node #{self.target_node}"
        
    @classmethod
    def from_dict(cls, data: dict) -> Cat:
        validate_dict(data, cls)
        return Cat(
            id=data['id'],
            name=data['name'],
            home=data['home'],
            traits=CatTraits.from_dict(data['traits']),
            needs=CatNeeds.from_dict(data['needs']),
            incapacitated_until=data['incapacitated_until'],
            memory=CatMemory.from_dict(data['memory']),
            current_node=data['current_node'],
            time_at_current_node=data['time_at_current_node'],
            stats= CatStats.from_dict(data['stats']),
            metrics= CatMetrics.from_dict(data['metrics']) if data['metrics'] is not None else None
            )

    def is_at_home(self):
        return self.current_node == self.home


@dataclass(frozen=True)
class Edge:
    node1: int
    node2: int

    @classmethod
    def from_dict(cls, data: dict) -> Edge:
        validate_dict(data, cls)
        return Edge(**data)

    def node_in_edge(self, node_id: int) -> bool:
        return node_id == self.node1 or node_id == self.node2

    def other_node(self, node_id: int) -> int:
        return self.node1 if self.node2 == node_id else self.node2

class NodeType(Enum):
      STREET = "street"
      HOUSE = "house"
      GARDEN = "garden"

@dataclass(frozen=True)
class Node:
    id: int
    node_type: NodeType

    @classmethod
    def from_dict(cls, data: dict) -> Node:
        validate_dict(data, cls)
        return Node(**data)

@dataclass(frozen=True)
class RelationshipTraits:
    cat1: int
    cat2: int

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipTraits:
        validate_dict(data, cls)
        return RelationshipTraits(**data)
        

@dataclass
class RelationshipStats:
    absolute_delta: float = 0
    min_value: float = 0
    max_value: float = 0
    number_of_sign_flips: int = 0
    interacted: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipStats:
        validate_dict(data, cls)
        return RelationshipStats(**data)
        

@dataclass
class Relationship:
    traits: RelationshipTraits
    value: int = 0
    stats: RelationshipStats = field(default_factory=RelationshipStats)
    metrics: Optional[RelationshipMetrics] = None

    def __str__(self):
        return f"Relationship: Cat {self.traits.cat1} - Cat {self.traits.cat2}"

    def __repr__(self):
        return f"Relationship between Cat {self.traits.cat1} and Cat {self.traits.cat2} - value: {self.value}"
    
    @classmethod
    def from_dict(cls, data: dict) -> Relationship:
        validate_dict(data, cls)
        return Relationship(
            traits=RelationshipTraits.from_dict(data['traits']),
            value=data['value'],
            stats= RelationshipStats.from_dict(data['stats']),
            metrics= RelationshipMetrics.from_dict(data['metrics']) if data['metrics'] is not None else None
            )

    @staticmethod
    def parse_key(key: str) -> tuple[int,int]:
        a,b = key.split('-')
        return int(a),int(b)

    def other_cat(self, cat1):
        return self.traits.cat1 if cat1 == self.traits.cat2 else self.traits.cat2

    def is_relationship(self, cat1, cat2):
        return (self.traits.cat1 == cat1 and self.traits.cat2 == cat2) or (
            self.traits.cat1 == cat2 and self.traits.cat2 == cat1
        )
