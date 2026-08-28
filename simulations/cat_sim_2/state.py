from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import List, Optional

from simulations.cat_sim_1.utils import validate_dict


class ActionType(Enum):
    SLEEP = "sleep"
    GROOM = "groom"
    EAT = "eat"
    HUNT = "hunt"
    MARK_TERRITORY = "mark_territory"
    GO_TOILET = "go_toilet"
    GREET_CAT = "greet_cat"
    GROOM_CAT = "groom_cat"
    GET_PET_BY_HUMAN = "get_pet_by_human"
    PLAY = "play"
    INVESTIGATE = "investigate"
    ATTACK_CAT = "attack_cat"

@dataclass
class CatMetrics:
    time_share_by_node_type: dict = field(default_factory=dict)
    time_share_by_action: dict = field(default_factory=dict)
    exploration_index: float = 0.0
    num_cats_interacted_with: int = 0
    amount_friendgroups: int = 0
    average_size_friendgroup: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> CatMetrics:
        validate_dict(data, cls)
        return CatMetrics(**data)

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
    primary_need: dict = field(default_factory= lambda: defaultdict(int))
    secondary_need: dict = field(default_factory= lambda: defaultdict(int))
    actions: dict = field(default_factory= lambda: defaultdict(int))
    times_at: dict = field(default_factory=lambda: defaultdict(int))
    path: list = field(default_factory=list)
    move_towards: dict = field(default_factory=lambda: defaultdict(int))
    interacted_with: dict = field(default_factory=lambda: defaultdict(int))
    incapacitation: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> CatStats:
        validate_dict(data, cls)
        return CatStats(
            **{k:v for k,v in data.items()}
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

@dataclass
class CatTickState:
    primary_need: Optional[NeedType] = None
    secondary_need: Optional[NeedType] = None
    action: Optional[ActionType] = None
    will_move_to: Optional[int] = None
    other_cat: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> CatTickState:
        validate_dict(data,cls)
        return CatTickState(**data)   

    def reset(self):
        self.primary_need = None
        self.secondary_need = None
        self.action = None
        self.will_move_to = None
        self.other_cat = None

@dataclass(eq=False)
class Cat:    
    id: int
    name: str
    home: int
    traits: CatTraits
    needs: dict[NeedType, float]
    incapacitated_until: Optional[int]
    memory: CatMemory
    current_node: int
    tick_state: CatTickState
    time_at_current_node:int = 0
    stats: CatStats = field(default_factory=CatStats)
    metrics: Optional[CatMetrics] = None

    def __post_init__(self):
        if self.current_node is None:
            self.current_node = self.home
        assert set(self.needs.keys()) == set(NeedType)


    def __str__(self):
        return f"{self.name} (n: #{self.current_node})"

    def __repr__(self):
        return f"{self.name} at node #{self.current_node}"
        
    @classmethod
    def from_dict(cls, data: dict) -> Cat:
        validate_dict(data, cls)
        return Cat(
            id=data['id'],
            name=data['name'],
            home=data['home'],
            traits=CatTraits.from_dict(data['traits']),
            needs={NeedType(k): v for k, v in data['needs'].items()},
            incapacitated_until=data['incapacitated_until'],
            memory=CatMemory.from_dict(data['memory']),
            current_node=data['current_node'],
            tick_state=CatTickState.from_dict(data['tick_state']),
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
    times_interacted: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipStats:
        validate_dict(data, cls)
        return RelationshipStats(**data)
        

@dataclass
class Relationship:
    traits: RelationshipTraits
    value: int = 0
    stats: RelationshipStats = field(default_factory=RelationshipStats)

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
