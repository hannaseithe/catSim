from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
import logging
import math
from typing import List, Optional, Set, Tuple, TypedDict
from simulations.cat_sim_2.state import (
    ActionType,
    Cat,
    CatMemory,
    CatMetrics,
    CatTickState,
    CatTraits,
    Edge,
    MemoryNode,
    NeedType,
    Node,
    NodeType,
    Relationship,
    RelationshipMetrics,
    RelationshipTraits,
    TraitType,
)
import random
import networkx as nx

from simulations.cat_sim_2.utils import validate_dict

logger = logging.getLogger(__name__)


NEED_THRESHOLDS = {
    "satisfied": 100,
    "open": 90,
    "urgent": 30,
    "critical": 10,
}

SCALE_MULTIPLIERS: dict[NeedType, dict[TraitType, float]] = {
    NeedType.EXPLORATION: {TraitType.CURIOSITY: 2, TraitType.CONFIDENCE: 2},
    NeedType.TERRITORY:   {TraitType.AGGRESSION: 2, TraitType.CONFIDENCE: 2},
    NeedType.SOCIAL:      {TraitType.AGGRESSION: -2, TraitType.CONFIDENCE: 2},
    NeedType.HUNT:        {TraitType.CONFIDENCE: 2},
    NeedType.HYGIENE:     {},
}

NEED_ACTION_OPTIONS: dict[NeedType, list[ActionType]] = {
    NeedType.HEALTH:      [ActionType.SLEEP, ActionType.GROOM],
    NeedType.FOOD:        [ActionType.EAT, ActionType.HUNT],
    NeedType.TOILET:      [ActionType.MARK_TERRITORY, ActionType.GO_TOILET],
    NeedType.ENERGY:      [ActionType.SLEEP],
    NeedType.SOCIAL:      [ActionType.GREET_CAT, ActionType.GROOM_CAT, ActionType.GET_PET_BY_HUMAN],
    NeedType.HUNT:        [ActionType.HUNT, ActionType.PLAY],
    NeedType.EXPLORATION: [ActionType.INVESTIGATE],
    NeedType.TERRITORY:   [ActionType.MARK_TERRITORY, ActionType.GREET_CAT, ActionType.GROOM_CAT, ActionType.ATTACK_CAT],
    NeedType.HYGIENE:     [ActionType.GROOM],
}


NODE_TYPE_ACTIONS: dict[NodeType, dict[str, list[ActionType]]] = {
    NodeType.STREET: {
        "available":   [ActionType.INVESTIGATE, ActionType.MARK_TERRITORY],
        "conditional": [],
        "uncertain":   [],
    },
    NodeType.HOUSE: {
        "available":   [ActionType.SLEEP, ActionType.EAT, ActionType.GROOM, ActionType.PLAY, ActionType.INVESTIGATE, ActionType.GET_PET_BY_HUMAN, ActionType.GO_TOILET],
        "conditional": [ActionType.GREET_CAT, ActionType.GROOM_CAT, ActionType.ATTACK_CAT],
        "uncertain":   [],
    },
    NodeType.GARDEN: {
        "available":   [ActionType.SLEEP, ActionType.INVESTIGATE, ActionType.PLAY, ActionType.GROOM, ActionType.MARK_TERRITORY, ActionType.GO_TOILET],
        "conditional": [ActionType.GREET_CAT, ActionType.GROOM_CAT, ActionType.ATTACK_CAT],
        "uncertain":   [ActionType.HUNT],
    },
}

ACTION_NEED_EFFECTS: dict[ActionType, dict[NeedType, float]] = {
    ActionType.SLEEP:          {NeedType.HEALTH: 0.5, NeedType.ENERGY: 1.5},
    ActionType.EAT:            {NeedType.FOOD: 40},
    ActionType.HUNT:           {NeedType.ENERGY: -5, NeedType.HUNT: 20},  # food: +20 * hunt_success_probability handled separately
    ActionType.INVESTIGATE:    {NeedType.EXPLORATION: 80},
    ActionType.PLAY:           {NeedType.HUNT: 10, NeedType.ENERGY: -4},
    ActionType.GROOM:          {NeedType.HYGIENE: 10, NeedType.HEALTH: 0.2},
    ActionType.MARK_TERRITORY: {NeedType.TERRITORY: 7, NeedType.TOILET: 4},
    ActionType.GREET_CAT:      {NeedType.SOCIAL: 5, NeedType.TERRITORY: 1},
    ActionType.GROOM_CAT:      {NeedType.SOCIAL: 15, NeedType.TERRITORY: 1},
    ActionType.ATTACK_CAT:     {NeedType.SOCIAL: -10, NeedType.TERRITORY: 25, NeedType.HEALTH: -5},
    ActionType.GET_PET_BY_HUMAN: {NeedType.SOCIAL: 5},
    ActionType.GO_TOILET:      {NeedType.TOILET: 80},
}

ACTION_LIKELIHOOD: dict[ActionType, float] = {
    ActionType.HUNT: 0.2
}

EDGE_TAX = 1
INVESTIGATE_NOVELTY_THRESHOLD = 0.1

NEED_DRAIN_EFFECTS: dict[NeedType, dict[str, float]] = {
    NeedType.FOOD:        {"satisfied": -1.7,   "open": -1.4,   "urgent": -0.04,  "critical": -0.004},
    NeedType.TOILET:      {"satisfied": -0.12,  "open": -6.67,  "urgent": -8.33,  "critical": -16.67},
    NeedType.ENERGY:      {"satisfied": -10.0,  "open": -0.2,   "urgent": -0.1,   "critical": -0.017},
    NeedType.SOCIAL:      {"satisfied": -0.069, "open": -0.104, "urgent": -0.017, "critical": -0.005},
    NeedType.HUNT:        {"satisfied": -2.5,   "open": -0.5,   "urgent": -0.83,  "critical": -0.012},
    NeedType.EXPLORATION: {"satisfied": -0.5,   "open": -0.4,   "urgent": -0.05,  "critical": -0.002},
    NeedType.TERRITORY:   {"satisfied": -0.83,  "open": -0.5,   "urgent": -0.083, "critical": -0.017},
    NeedType.HYGIENE:     {"satisfied": -1.67,  "open": -0.21,  "urgent": -0.035, "critical": -0.005},
}


class EventDict(TypedDict):
    node_type: List[NodeType]
    probability: float
    need_effects: dict[NeedType, float]

class InteractiveEventDict(EventDict):
    relationship_effect: float

EVENTS: dict[str, EventDict] = {
    "falling_from_tree": {
        "node_type": [NodeType.GARDEN],
        "probability": 0.0005,
        "need_effects": {NeedType.HEALTH: -10, NeedType.ENERGY: -5},
    },
    "hit_by_car": {
        "node_type": [NodeType.STREET],
        "probability": 0.005,
        "need_effects": {NeedType.HEALTH: -60},
    },
    "infection": {
        "node_type": [NodeType.GARDEN],
        "probability": 0.0005,
        "need_effects": {NeedType.HEALTH: -20},
    },
    "dog_attack": {
        "node_type": [NodeType.GARDEN],
        "probability": 0.001,
        "need_effects": {NeedType.HEALTH: -30, NeedType.ENERGY: -10},
    },
}

INTERACTIVE_EVENTS: dict[ActionType, InteractiveEventDict] = {
    ActionType.ATTACK_CAT: {
        "node_type": [NodeType.GARDEN, NodeType.HOUSE],
        "probability": 0.1,  # assumed probability if enemy remembered at node
        "need_effects": {NeedType.HEALTH: -10, NeedType.SOCIAL: -5, NeedType.TERRITORY: -5, NeedType.HYGIENE: -5, NeedType.ENERGY: -10},
        "relationship_effect": -2,
    },
    ActionType.GREET_CAT: {
        "node_type": [NodeType.GARDEN, NodeType.HOUSE],
        "probability": 0.1,  # assumed probability if neutral or friend remembered at node
        "need_effects": {NeedType.SOCIAL: 3, NeedType.TERRITORY: 1},
        "relationship_effect": 0.5,        
    },
    ActionType.GROOM_CAT: {
        "node_type": [NodeType.GARDEN, NodeType.HOUSE],
        "probability": 0.1,  # assumed probability if friend remembered at node
        "need_effects": {NeedType.SOCIAL: 3, NeedType.TERRITORY: 1, NeedType.HYGIENE: 5},
        "relationship_effect": 2,
    },
}

def _compute_event_expected_effects() -> dict[NodeType, dict[NeedType, float]]:
    result: dict[NodeType, dict[NeedType, float]] = {nt: {} for nt in NodeType}
    for event in EVENTS.values():
        for node_type in event["node_type"]:
            prob = event["probability"]
            for need, effect in event["need_effects"].items():
                result[node_type][need] = result[node_type].get(need, 0) + prob * effect
    return result

EVENT_EXPECTED_EFFECTS: dict[NodeType, dict[NeedType, float]] = _compute_event_expected_effects()

def get_threshold(value: float) -> str:
    if value < NEED_THRESHOLDS['critical']:
        return 'critical'
    if value < NEED_THRESHOLDS['urgent']:
        return 'urgent'
    if value < NEED_THRESHOLDS['open']:
        return 'open'
    return 'satisfied'

def urgency_score(cat:Cat, need: Tuple[NeedType,float]):
    result = 100 - need[1]
    for trait, sm in SCALE_MULTIPLIERS.get(need[0], {}).items():
        result += getattr(cat.traits,trait.value) * sm
    return result


def identify_primary_needs(cat: Cat) -> tuple[NeedType, NeedType]:
    result: list[NeedType] = []
    need_groups: list[list[NeedType]] = [[], [], [], []]
    needs_list = list(cat.needs.items())
    first_four = needs_list[:4]
    last_five = needs_list[4:]
    threshold_to_group = {'critical': 0, 'urgent': 1, 'open': 2, 'satisfied': 3}

    # Critical/urgent: survival needs (first_four) always go first
    for need_type, value in first_four:
        t = get_threshold(value)
        if t in ('critical', 'urgent'):
            need_groups[threshold_to_group[t]].append(need_type)
    for need_type, value in sorted(last_five, key=lambda n: urgency_score(cat, n), reverse=True):
        t = get_threshold(value)
        if t in ('critical', 'urgent'):
            need_groups[threshold_to_group[t]].append(need_type)

    # Open/satisfied: all needs compete by urgency_score
    for need_type, value in sorted(needs_list, key=lambda n: urgency_score(cat, n), reverse=True):
        t = get_threshold(value)
        if t in ('open', 'satisfied'):
            need_groups[threshold_to_group[t]].append(need_type)

    for group in need_groups:
        if len(result) >= 2:
            break
        for need_type in group:
            if len(result) >= 2:
                break
            result.append(need_type)
    return result[0], result[1]


def apply_events(node_type: NodeType, cat: Cat) -> None:
    for event in EVENTS.values():
        if node_type in event["node_type"]:
            if random.random() < event["probability"]:
                for need, value in event["need_effects"].items():
                    cat.needs[need] += value


def choose_action(primary_need: NeedType, secondary_need: NeedType, available_actions: list[ActionType], m_node: MemoryNode) -> ActionType | None:
    if not available_actions:
        return None
    action_score: float = 0.0
    chosen_action = available_actions[0]
    for action in available_actions:
        if action == ActionType.INVESTIGATE and primary_need == NeedType.EXPLORATION:
            novelty = m_node.novelty_score if m_node is not None else 1.0
            a_s = ACTION_NEED_EFFECTS[ActionType.INVESTIGATE].get(NeedType.EXPLORATION, 0.0) * novelty
        else:
            a_s = ACTION_NEED_EFFECTS[action].get(primary_need, 0) * 3 + ACTION_NEED_EFFECTS[action].get(secondary_need, 0)
        if a_s > action_score:
            action_score = a_s
            chosen_action = action
    return chosen_action


def clamp_needs(cat: Cat) -> None:
    for need in cat.needs:
        cat.needs[need] = max(0.0, min(100.0, cat.needs[need]))


def safe_log(x):
    if x <= 0:
        return 0.0
    return math.log(x)


class SimulationEncoder(json.JSONEncoder):
    # method called for unrecognized values
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def fix_tuple_keys_dict(obj):
    if isinstance(obj, dict):
        return {
            (
                f"{key[0]}-{key[1]}" if isinstance(key, tuple) else key
            ): fix_tuple_keys_dict(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [fix_tuple_keys_dict(el) for el in obj]
    else:
        return obj


@dataclass
class SimulationMetrics:
    friendgroups_total: int
    average_size_friendgroups: int
    largest_group_size: int
    isolated_cats_count: int
    mean_relationship_value: float
    interaction_density: float


@dataclass(frozen=True)
class SimulationParameters:
    iterations: int = 1000
    seed: int = 0
    cat_amount: int = 10
    node_amount: int = 100
    mean_edges: int = 4
    var_edges: float = 1.0
    house_ratio: float = 0.2
    garden_ratio: float = 0.5
    mean_aggression: float = 0.0
    var_aggression: float = 5.0
    mean_confidence: float = 0.0
    var_confidence: float = 5.0
    mean_curiosity: float = 0.0
    var_curiosity: float = 5.0
    mean_activeness: float = 0.0
    var_activeness: float = 5.0
    mean_strength: float = 0.0
    var_strength: float = 5.0
    initial_need_level: float = 70.0

    def __post_init__(self):
        if self.iterations <= 0:
            raise ValueError("iterations must be greater than 0")


@dataclass
class SimulationStats:
    total_number_interactions: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> SimulationStats:
        validate_dict(data, cls)
        return SimulationStats(**data)


@dataclass
class SimulationIter:
    tick: int = 0
    finished: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> SimulationIter:
        validate_dict(data, cls)
        return SimulationIter(**data)


@dataclass
class SimulationState:
    cats: dict[int,Cat] = field(default_factory=dict)
    relationships: dict[tuple[int, int], Relationship] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    nodes: dict[int, Node] = field(default_factory=dict)
    run: SimulationIter = field(default_factory=SimulationIter)
    stats: SimulationStats = field(default_factory=SimulationStats)

    @classmethod
    def from_dict(cls, data: dict) -> SimulationState:
        validate_dict(data, cls)
        return SimulationState(
            cats={int(id): Cat.from_dict(s_cat) for id, s_cat in data["cats"].items()},
            relationships={
                Relationship.parse_key(key): Relationship.from_dict(s_rel)
                for key, s_rel in data["relationships"].items()
            },
            edges=[Edge.from_dict(s_edge) for s_edge in data["edges"]],
            nodes={int(id): Node.from_dict(s_node) for id, s_node in data["nodes"].items()},
            run=SimulationIter.from_dict(data["run"]),
            stats=SimulationStats.from_dict(
                data["stats"],
            ),
        )


class Simulation:
    def __init__(self, params: SimulationParameters = SimulationParameters()):
        self.params = params

        random.seed(self.params.seed)

        self.state: SimulationState = SimulationState()

        self.metrics: Optional[SimulationMetrics] = None

    def get_node(self, node_id: int) -> Node | None:
        return self.state.nodes[node_id]

    def get_nodes_edges(self, node_id: int) -> list[Edge]:
        result = []
        for edge in self.state.edges:
            if edge.node_in_edge(node_id):
                result.append(edge)
        return result

    def get_neighboring_nodes(self, node_id: int) -> list[int]:
        result = []
        for edge in self.state.edges:
            if edge.node_in_edge(node_id):
                result.append(edge.other_node(node_id))
        return result

    def is_home_of_enemy(self, node_id: int, cat_id: int) -> bool:
        home_cats = [
            cat.id for cat in self.state.cats.values() if cat.home == node_id
        ]
        if cat_id in home_cats:
            return False
        return any(self.get_relationship(cat, cat_id).value < -1e-9 for cat in home_cats)

    def is_home_of_friend(self, node_id: int, cat_id: int) -> bool:
        home_cats = [
            cat.id for cat in self.state.cats.values() if cat.home == node_id
        ]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat, cat_id).value > 1e-9:
                return True
        return False

    def is_neutral_node(self, node_id: int) -> bool:
        home_cats = [
            cat.id for cat in self.state.cats.values() if cat.home == node_id
        ]
        return len(home_cats) == 0

    def get_neighboring_nodes_no_enemy(self, node_id: int, cat_id: int) -> list[int]:
        result = self.get_neighboring_nodes(node_id)
        result_copy = result.copy()
        for node in result_copy:
            if self.is_home_of_enemy(node, cat_id):
                result.remove(node)
        return result

    def get_cat(self, cat_id) -> Cat | None:
        return self.state.cats[cat_id]

    def get_cats_on_node(self, node_id: int) -> list[int]:
        result = []
        for cat in self.state.cats.values():
            if cat.current_node == node_id:
                result.append(cat.id)
        return result

    def is_enemy(self, cat1: int, cat2: int) -> bool:
        if cat1 == cat2:
            return False
        return self.get_relationship(cat1, cat2).value < -1e-9

    def get_enemies_on_node(self, cat:Cat) -> list[int]:
        return [id for id in self.get_cats_on_node(cat.current_node) if self.is_enemy(cat.id, id)]

    def is_enemy_here(self, cat: Cat) -> bool:
        return any(
            self.get_relationship(cat.id, other_id).value < -1e-9
            for other_id in self.get_cats_on_node(cat.current_node)
            if other_id != cat.id
        )

    def seen_enemy(self, cat: Cat, node_id: int) -> bool:
        memory_node = cat.memory.visited_nodes.get(node_id)
        if not memory_node:
            return False
        return any(
            self.is_enemy(cat.id, other_id)
            for other_id in memory_node.last_seen_cats
        )

    def is_friend(self, cat1: int, cat2: int) -> bool:
        if cat1 == cat2:
            return False
        return self.get_relationship(cat1, cat2).value > 1e-9

    def get_friends_on_node(self, cat:Cat) -> list[int]:
        return [id for id in self.get_cats_on_node(cat.current_node) if self.is_friend(cat.id, id)]
    
    def is_friend_here(self, cat: Cat) -> bool:
        return any(
            self.is_friend(cat.id, other_id)
            for other_id in self.get_cats_on_node(cat.current_node)
        )
    def seen_friendly(self, cat: Cat, node_id: int) -> bool:
        memory_node = cat.memory.visited_nodes.get(node_id)
        if not memory_node:
            return False
        return any(
            self.is_friend(cat.id, other_id)
            for other_id in memory_node.last_seen_cats
        )

    def is_neutral(self, cat1: int, cat2: int) -> bool:
        if cat1 == cat2:
            return False
        return abs(self.get_relationship(cat1, cat2).value) <= 1e-9

    def get_neutral_on_node(self, cat:Cat) -> list[int]:
        return [id for id in self.get_cats_on_node(cat.current_node) if self.is_neutral(cat.id, id)]

    def is_neutral_here(self, cat: Cat) -> bool:
        return any(
            self.is_neutral(cat.id, other_id)
            for other_id in self.get_cats_on_node(cat.current_node)
        )

    def seen_neutral(self, cat: Cat, node_id: int) -> bool:
        memory_node = cat.memory.visited_nodes.get(node_id)
        if not memory_node:
            return False
        return any(
            self.is_neutral(cat.id,other_id)
            for other_id in memory_node.last_seen_cats
        )

    def memory_distance(self, cat: Cat, target_node_id: int) -> tuple[int, list[int]]:
        known_nodes = cat.memory.visited_nodes
        known_edges = [e for e in self.state.edges if e.node1 in known_nodes or e.node2 in known_nodes]
        visited = {cat.current_node}
        queue = [(cat.current_node, 0)]
        parent: dict[int, int | None] = {cat.current_node: None}
        while queue:
            node_id, distance = queue.pop(0)
            if node_id == target_node_id:
                path = []
                current: int | None = target_node_id
                while current is not None:
                    path.append(current)
                    current = parent[current]
                path.reverse()
                return distance, path
            for edge in known_edges:
                if edge.node_in_edge(node_id):
                    neighbour = edge.other_node(node_id)
                    if neighbour not in visited:
                        visited.add(neighbour)
                        parent[neighbour] = node_id
                        queue.append((neighbour, distance + 1))
        return 0, []

    def expected_event_effect(self, cat: Cat, node_id: int, primary_need: NeedType, secondary_need: NeedType) -> float:
        node_type = self.state.nodes[node_id].node_type
        effects = dict(EVENT_EXPECTED_EFFECTS[node_type])
        #consider the conseqences of other cats possible actions based on cats memory as "events"
        cat_attack = INTERACTIVE_EVENTS[ActionType.ATTACK_CAT]
        cat_greet = INTERACTIVE_EVENTS[ActionType.GREET_CAT]
        cat_groom = INTERACTIVE_EVENTS[ActionType.GROOM_CAT]
        if self.seen_enemy(cat, node_id) and node_type in cat_attack["node_type"]:
            for need, value in cat_attack["need_effects"].items():
                effects[need] = effects.get(need, 0) + value * cat_attack["probability"]
        if self.seen_neutral(cat, node_id) and node_type in cat_greet["node_type"]:
            for need, value in cat_greet["need_effects"].items():
                effects[need] = effects.get(need, 0) + value * cat_greet["probability"]
        if self.seen_friendly(cat,node_id) and node_type in cat_groom["node_type"]:
            for need, value in cat_groom["need_effects"].items():
                effects[need] = effects.get(need, 0) + value * cat_groom["probability"]
        return effects.get(primary_need, 0) * 3 + effects.get(secondary_need, 0)

    def get_relationship(self, cat1: int, cat2: int):
        a, b = sorted((cat1, cat2))
        return self.state.relationships.get((a,b))

    def get_friends(self, cat1: int) -> list [int]:
        result = []
        for rel in self.state.relationships.values():
            if (
                cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2
            ) and rel.value > 1e-9:
                result.append(rel.other_cat(cat1))
        return result

    def get_enemies(self, cat1: int) -> list[int]:
        result = []
        for rel in self.state.relationships.values():
            if (
                cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2
            ) and rel.value < -1e-9:
                result.append(rel.other_cat(cat1))
        return result

    def generate_initial_nodes(self) -> None:
        n = self.params.node_amount
        n_houses = round(n * self.params.house_ratio)
        n_gardens = round(n * self.params.garden_ratio)
        n_streets = n - n_houses - n_gardens
        node_types = ([NodeType.HOUSE] * n_houses
                      + [NodeType.GARDEN] * n_gardens
                      + [NodeType.STREET] * n_streets)
        random.shuffle(node_types)
        for i, node_type in enumerate(node_types):
            self.state.nodes[i] = Node(id=i, node_type=node_type)

    def generate_initial_edges(self) -> None:
        edge_sigma = self.params.var_edges ** 0.5
        # Spanning tree ensures full connectivity
        available = list(range(self.params.node_amount))
        connected = [available.pop(0)]
        while available:
            n1 = random.choice(connected)
            n2 = available.pop(random.randint(0, len(available) - 1))
            self.state.edges.append(Edge(node1=n1, node2=n2))
            connected.append(n2)
        # Extra edges to approach target degree
        for node_id in range(self.params.node_amount):
            target = max(1, round(random.gauss(self.params.mean_edges, edge_sigma)))
            current = len(self.get_nodes_edges(node_id))
            candidates = [i for i in range(self.params.node_amount) if i != node_id]
            random.shuffle(candidates)
            for candidate in candidates:
                if current >= target:
                    break
                already = any(
                    (e.node1 == node_id and e.node2 == candidate)
                    or (e.node1 == candidate and e.node2 == node_id)
                    for e in self.state.edges
                )
                if not already:
                    self.state.edges.append(Edge(node1=node_id, node2=candidate))
                    current += 1

    def generate_initial_cats(self) -> None:
        house_nodes = [nid for nid, node in self.state.nodes.items() if node.node_type == NodeType.HOUSE]
        def clamp_trait(mean: float, var: float) -> float:
            return max(-10.0, min(10.0, random.gauss(mean, var ** 0.5)))
        for i in range(self.params.cat_amount):
            home_id = random.choice(house_nodes)
            traits = CatTraits(
                aggression=clamp_trait(self.params.mean_aggression, self.params.var_aggression),
                confidence=clamp_trait(self.params.mean_confidence, self.params.var_confidence),
                curiosity=clamp_trait(self.params.mean_curiosity, self.params.var_curiosity),
                activeness=clamp_trait(self.params.mean_activeness, self.params.var_activeness),
                strength=clamp_trait(self.params.mean_strength, self.params.var_strength),
            )
            self.state.cats[i] = Cat(
                id=i,
                name=f"cat-{i}",
                home=home_id,
                traits=traits,
                needs={need: self.params.initial_need_level for need in NeedType},
                incapacitated_until=None,
                memory=CatMemory(visited_nodes={home_id: MemoryNode(novelty_score=1.0, last_seen_cats=[])}),
                current_node=home_id,
                tick_state=CatTickState(),
            )

    def generate_initial_relationships(self) -> None:
        cat_ids = list(self.state.cats.keys())
        for i, cat1 in enumerate(cat_ids):
            for cat2 in cat_ids[i + 1:]:
                a, b = sorted((cat1, cat2))
                self.state.relationships[(a, b)] = Relationship(
                    traits=RelationshipTraits(cat1=a, cat2=b)
                )

    def generate_initial_state(self):
        self.generate_initial_nodes()
        self.generate_initial_edges()
        self.generate_initial_cats()
        self.generate_initial_relationships()
        
    def serialize_state(self) -> str:
        return json.dumps(
            fix_tuple_keys_dict(asdict(self.state)), cls=SimulationEncoder
        )
    
    #TODO
    def set_stats_at_node(self, cat: Cat, choice: str | int):
        assert cat.current_node is not None
        cat.time_at_current_node += 1
        if cat.is_at_home():
            cat.stats.iter_at_home += 1
            if not choice == "stay":
                cat.stats.times_at_home += 1
        elif self.is_neutral_node(cat.current_node):
            cat.stats.iter_at_neutral += 1
            if not choice == "stay":
                cat.stats.times_at_neutral += 1
        else:
            cat.stats.iter_at_friendly += 1
            if not choice == "stay":
                cat.stats.times_at_friendly += 1

    
    def get_action_probability(self, cat: Cat, node_id: int, node_type: NodeType, action: ActionType) -> float:
        if action in NODE_TYPE_ACTIONS[node_type]["uncertain"]:
            return ACTION_LIKELIHOOD[action]
        if action in NODE_TYPE_ACTIONS[node_type]["conditional"]:
            if action == ActionType.ATTACK_CAT and self.seen_enemy(cat, node_id):
                return 0.4
            if action == ActionType.GREET_CAT and (self.seen_neutral(cat, node_id) or self.seen_friendly(cat, node_id)):
                return 0.6
            if action == ActionType.GROOM_CAT and self.seen_friendly(cat, node_id):
                return 0.4
            return 0.0
        return 1.0

    def score_node(self, cat: Cat, node_id: int, m_node: MemoryNode, primary_need: NeedType, secondary_need: NeedType) -> tuple[float, int | None]:
        node = self.state.nodes[node_id]
        relevant_actions = set(NEED_ACTION_OPTIONS[primary_need] + NEED_ACTION_OPTIONS[secondary_need])
        possible_actions = [
            action for action in relevant_actions
            if action in NODE_TYPE_ACTIONS[node.node_type]["available"]
            or action in NODE_TYPE_ACTIONS[node.node_type]["conditional"]
            or action in NODE_TYPE_ACTIONS[node.node_type]["uncertain"]
        ]
        if not possible_actions:
            return 0.0, None
        action_score: float = 0.0
        for action in possible_actions:
            if action == ActionType.INVESTIGATE and primary_need == NeedType.EXPLORATION:
                novelty = m_node.novelty_score if m_node is not None else 1.0
                a_s = ACTION_NEED_EFFECTS[ActionType.INVESTIGATE].get(NeedType.EXPLORATION, 0.0) * novelty
            else:
                prob = self.get_action_probability(cat, node_id, node.node_type, action)
                a_s = prob * (ACTION_NEED_EFFECTS[action].get(primary_need, 0) * 3 + ACTION_NEED_EFFECTS[action].get(secondary_need, 0))
            if a_s > action_score:
                action_score = a_s
        distance, path = self.memory_distance(cat, node_id)
        node_score = action_score - EDGE_TAX * distance + self.expected_event_effect(cat, node_id, primary_need, secondary_need)
        return node_score, path[1] if len(path) > 1 else None

    def primary_need_has_viable_node(self, cat: Cat, need: NeedType) -> bool:
        actions = NEED_ACTION_OPTIONS[need]
        for node_id in cat.memory.visited_nodes:
            node_type = self.state.nodes[node_id].node_type
            for action in actions:
                if action in NODE_TYPE_ACTIONS[node_type]["available"]:
                    return True
        return False

    def get_chosen_node(self, cat: Cat) -> tuple[int | None, int | None]:
        primary_need = cat.tick_state.primary_need
        secondary_need = cat.tick_state.secondary_need
        if primary_need is None or secondary_need is None:
            return None, None
        if primary_need != NeedType.EXPLORATION and not self.primary_need_has_viable_node(cat, primary_need):
            primary_need = NeedType.EXPLORATION
        node_scores: list[tuple[int, float, int | None]] = []
        unknown_adjacent_nodes: Set[int] = set()
        for node_id, m_node in cat.memory.visited_nodes.items():
            if self.is_home_of_enemy(node_id, cat.id):
                continue
            for a_node in self.get_neighboring_nodes(node_id):
                if a_node not in cat.memory.visited_nodes:
                    unknown_adjacent_nodes.add(a_node)
            node_score, next_node = self.score_node(cat, node_id, m_node, primary_need, secondary_need)
            node_scores.append((node_id, node_score, next_node))
        if primary_need == NeedType.EXPLORATION:
            exploration_weight = 3
        elif secondary_need == NeedType.EXPLORATION:
            exploration_weight = 1
        else:
            exploration_weight = 0
        for node_id in unknown_adjacent_nodes:
            if self.is_home_of_enemy(node_id, cat.id):
                continue
            distance, path = self.memory_distance(cat, node_id)
            node_score = ACTION_NEED_EFFECTS[ActionType.INVESTIGATE].get(NeedType.EXPLORATION, 0) * exploration_weight - EDGE_TAX * distance
            node_scores.append((node_id, node_score, path[1] if len(path) > 1 else None))
        result = max(node_scores, key=lambda x: x[1])
        return result[0], result[2] 


    def decision_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            # identify primary and secondary need
            cat.tick_state.primary_need, cat.tick_state.secondary_need = identify_primary_needs(cat)
            # chose node
            _, next_node = self.get_chosen_node(cat)
            cat.tick_state.will_move_to = next_node

    def movement_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            if cat.tick_state.will_move_to is not None:
                cat.current_node = cat.tick_state.will_move_to


    def event_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            node = self.get_node(cat.current_node)
            if node is not None:
                apply_events(node.node_type, cat)
            clamp_needs(cat)

    def get_available_actions(self, cat: Cat) -> list[ActionType]:
        if cat.current_node not in cat.memory.visited_nodes:
            return [ActionType.INVESTIGATE]
        node = self.get_node(cat.current_node)
        if node is None:
            return []
        available: list[ActionType] = [
            a for a in NODE_TYPE_ACTIONS[node.node_type]["available"]
            if a != ActionType.INVESTIGATE
            or cat.memory.visited_nodes[cat.current_node].novelty_score > INVESTIGATE_NOVELTY_THRESHOLD
        ]
        conditional = NODE_TYPE_ACTIONS[node.node_type]["conditional"]
        if ActionType.ATTACK_CAT in conditional and self.is_enemy_here(cat):
            available.append(ActionType.ATTACK_CAT)
        if ActionType.GREET_CAT in conditional and (self.is_neutral_here(cat) or self.is_friend_here(cat)):
            available.append(ActionType.GREET_CAT)
        if ActionType.GROOM_CAT in conditional and self.is_friend_here(cat):
            available.append(ActionType.GROOM_CAT)
        if ActionType.HUNT in NODE_TYPE_ACTIONS[node.node_type]["uncertain"] and random.random() < ACTION_LIKELIHOOD[ActionType.HUNT]:
            available.append(ActionType.HUNT)
        return available

    def apply_interactive_action(self, cat: Cat, chosen_action: ActionType) -> None:
        if chosen_action == ActionType.ATTACK_CAT:
            enemies = self.get_enemies_on_node(cat)
            chosen_cat = min(enemies, key=lambda e: self.get_relationship(cat.id, e).value)
        elif chosen_action == ActionType.GREET_CAT:
            chosen_cat = random.choice(self.get_friends_on_node(cat) + self.get_neutral_on_node(cat))
        else:  # GROOM_CAT
            friends = self.get_friends_on_node(cat)
            chosen_cat = max(friends, key=lambda f: self.get_relationship(cat.id, f).value)
        cat.tick_state.other_cat = chosen_cat
        cat2 = self.get_cat(chosen_cat)
        if cat2 is not None:
            for need, value in INTERACTIVE_EVENTS[chosen_action]["need_effects"].items():
                cat2.needs[need] += value
            if chosen_action == ActionType.ATTACK_CAT:
                strength_diff = cat.traits.strength - cat2.traits.strength
                cat.needs[NeedType.HEALTH] += -strength_diff * 0.15
                cat2.needs[NeedType.HEALTH] += strength_diff * 0.15
            clamp_needs(cat2)
            rel = self.get_relationship(cat.id, cat2.id)
            if rel is not None:
                rel.value += INTERACTIVE_EVENTS[chosen_action]["relationship_effect"]

    def action_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            if cat.tick_state.will_move_to is not None:
                continue
            if cat.tick_state.primary_need is None or cat.tick_state.secondary_need is None:
                continue
            available_actions = self.get_available_actions(cat)
            m_node = cat.memory.visited_nodes.get(cat.current_node)
            if m_node is not None:
                chosen_action = choose_action(cat.tick_state.primary_need, cat.tick_state.secondary_need, available_actions, m_node)
                cat.tick_state.action = chosen_action
            if chosen_action is not None:
                for need, value in ACTION_NEED_EFFECTS[chosen_action].items():
                    cat.needs[need] += value
                if chosen_action == ActionType.HUNT and random.random() < (0.6 + cat.traits.strength / 100):
                    cat.needs[NeedType.FOOD] += 20
                if chosen_action in INTERACTIVE_EVENTS:
                    self.apply_interactive_action(cat, chosen_action)
            clamp_needs(cat)

    def memory_update_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            cats_on_node = self.get_cats_on_node(cat.current_node)
            cats_on_node.remove(cat.id)
            if cat.current_node in cat.memory.visited_nodes:
                m = cat.memory.visited_nodes[cat.current_node]
                m.last_seen_cats = cats_on_node
                if cat.tick_state.action == ActionType.INVESTIGATE:
                    m.novelty_score = max(0.0, m.novelty_score - 0.1)
                else:
                    m.novelty_score = max(0.0, m.novelty_score - 0.01)
            elif cat.tick_state.action == ActionType.INVESTIGATE:
                cat.memory.visited_nodes[cat.current_node] = MemoryNode(novelty_score=0.6, last_seen_cats=cats_on_node)
            

    def drain_step(self):
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None:
                continue
            for need in NEED_DRAIN_EFFECTS:
                cat.needs[need] += NEED_DRAIN_EFFECTS[need][get_threshold(cat.needs[need])]
            clamp_needs(cat)
            for id, m_node in cat.memory.visited_nodes.items():
                if id == cat.current_node:
                    continue
                m_node.novelty_score = min(1.0, m_node.novelty_score + 0.01)

    def incapacitation_step(self) -> None:
        tick = self.state.run.tick
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.incapacitated_until is not None and tick >= cat.incapacitated_until:
                cat.incapacitated_until = None
                if cat.needs[NeedType.HEALTH] <= 0:
                    cat.needs[NeedType.HEALTH] = 10.0
                if cat.needs[NeedType.FOOD] <= 0:
                    cat.needs[NeedType.FOOD] = 10.0
            elif cat.incapacitated_until is None:
                if cat.needs[NeedType.HEALTH] <= 0 or cat.needs[NeedType.FOOD] <= 0:
                    cat.incapacitated_until = tick + 2016
                    cat.current_node = cat.home
                    cat.needs[NeedType.HEALTH] = max(cat.needs[NeedType.HEALTH], 0.0)
                    cat.needs[NeedType.FOOD] = max(cat.needs[NeedType.FOOD], 0.0)

    def reset_tick_state_step(self):
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            cat.tick_state.reset()      
            
            

    #TODO
    def set_general_engagement_stats(self, rel: Relationship) -> None:
        rel.stats.absolute_delta += 0.05
        self.state.stats.total_number_interactions += 1
        rel.stats.interacted = True
        if abs(rel.value) < 1e-9:
            rel.stats.number_of_sign_flips += 1

    def set_fight_stats(self, cat1: Cat, cat2: Cat, rel: Relationship) -> None:
        cat1.stats.fights += 1
        cat1.stats.interacted_with.add(cat2.id)
        cat2.stats.fights += 1
        cat2.stats.interacted_with.add(cat1.id)
        if rel.value > rel.stats.max_value:
            rel.stats.max_value = rel.value

    def set_friendly_engagement_stats(self, cat1: Cat, cat2: Cat, rel: Relationship) -> None:
        cat1.stats.friendly_interaction += 1
        cat1.stats.interacted_with.add(cat2.id)
        cat2.stats.friendly_interaction += 1
        cat2.stats.interacted_with.add(cat1.id)
        if rel.value < rel.stats.min_value:
            rel.stats.min_value = rel.value

    def set_relationship_metrics(self, G):
        #TODO: Adapt / Implement
        for rel in self.state.relationships.values():
            rel.metrics = RelationshipMetrics(
                stability=1 / (1 + rel.stats.absolute_delta),
                volatility=rel.stats.absolute_delta / self.params.iterations,
                min_value=rel.stats.min_value,
                max_value=rel.stats.max_value,
                number_of_sign_flips=rel.stats.number_of_sign_flips,
            )
            if abs(rel.value) < -1e-9:
                G.add_edge(rel.traits.cat1, rel.traits.cat2)


    def set_cat_metrics(self, cliques):
        #TODO: Adapt / Implement
        for cat in self.state.cats:
            total_connections = len(cat.stats.interacted_with)
            prob_friends = (
                0
                if total_connections == 0
                else len(self.get_friends(cat.traits.id)) / total_connections
            )
            prob_enemies = (
                0
                if total_connections == 0
                else len(self.get_enemies(cat.traits.id)) / total_connections
            )
            prob_aqua = 0 if total_connections == 0 else 1 - prob_friends - prob_enemies
            config = {
                "percent_time_spent_home": cat.stats.iter_at_home
                / self.params.iterations,
                "percent_time_spent_on_edge": cat.stats.iter_on_edge
                / self.params.iterations,
                "percent_time_spent_on_neutral_ground": cat.stats.iter_at_neutral
                / self.params.iterations,
                "percent_time_spent_at_friends_house": cat.stats.iter_at_friendly
                / self.params.iterations,
                "average_iter_spent_at_home": cat.stats.iter_at_home
                / cat.stats.times_at_home
                if cat.stats.times_at_home > 0
                else 0,
                "average_iter_spent_at_friends_home": cat.stats.iter_at_friendly
                / cat.stats.times_at_friendly
                if cat.stats.times_at_friendly > 0
                else 0,
                "average_iter_spent_on_neutral_node": cat.stats.iter_at_neutral
                / cat.stats.times_at_neutral
                if cat.stats.times_at_neutral > 0
                else 0,
                "percent_of_cats_interacted_with": total_connections
                / (self.params.cat_amount - 1),
                "percent_of_friends": 0
                if total_connections == 0
                else prob_friends / total_connections,
                "percent_of_enemies": 0
                if total_connections == 0
                else prob_enemies / total_connections,
                "percent_of_aquaintances": 0
                if total_connections == 0
                else prob_aqua / total_connections,
                "percent_time_spent_fighting": cat.stats.fights
                / self.params.iterations,
                "percent_time_spent_friendly_interaction": cat.stats.friendly_interaction
                / self.params.iterations,
                "percent_time_spent_sleeping": cat.stats.sleeps
                / self.params.iterations,
                "exploration_index": len(cat.stats.nodes_visited)
                / self.params.node_amount,
                "relationship_entropy": -(
                    prob_friends * safe_log(prob_friends)
                    + prob_enemies * safe_log(prob_enemies)
                    + prob_aqua * safe_log(prob_aqua)
                ),
            }

            cats_cliques = [clique for clique in cliques if cat.traits.id in clique]

            config["amount_friendgroups"] = len(cats_cliques)

            config["average_size_friendgroup"] = (
                0
                if len(cats_cliques) == 0
                else sum([len(clique) for clique in cats_cliques])
                / config["amount_friendgroups"]
            )
            cat.metrics = CatMetrics(**config)


    def set_simulation_metrics(self, cliques):
        #TODO: adapt / implement
        max_interactions_per_iteration = self.params.cat_amount // 2  # floor division
        max_total_interactions = self.params.iterations * max_interactions_per_iteration

        interaction_density = (
            self.state.stats.total_number_interactions / max_total_interactions
        )

        average_size_friendgroups = (
            0
            if len(cliques) == 0
            else sum([len(clique) for clique in cliques]) / len(cliques)
        )

        largest_group_size = (
            0 if len(cliques) <= 0 else max(len(clique) for clique in cliques)
        )

        isolated_cats = [
            cat for cat in self.state.cats if cat.metrics.percent_of_friends == 0
        ]

        relationship_values = [
            rel.value
            for rel in self.state.relationships.values()
            if rel.stats.interacted
        ]
        mean_relationship_value = (
            0
            if len(relationship_values) == 0
            else sum(relationship_values) / len(relationship_values)
        )

        self.metrics = SimulationMetrics(
            friendgroups_total=len(cliques),
            average_size_friendgroups=average_size_friendgroups,
            largest_group_size=largest_group_size,
            interaction_density=interaction_density,
            isolated_cats_count=len(isolated_cats),
            mean_relationship_value=mean_relationship_value,
        )


    def calculate_metrics(self):  # TODO: implement
        return
        #TODO: adapt / implement
        G = nx.Graph()

        G.add_nodes_from(range(self.params.node_amount))

        self.set_relationship_metrics(G)

        cliques = [clique for clique in list(nx.find_cliques(G)) if len(clique) > 2]
        self.set_cat_metrics(cliques)
        self.set_simulation_metrics(cliques)

    def step(self):
        self.reset_tick_state_step()
        self.decision_step()
        self.movement_step()
        self.event_step()
        self.action_step()
        self.memory_update_step()
        self.drain_step()
        self.incapacitation_step()
        #self.set_stats_step()
        self.state.run.tick += 1
        if self.state.run.tick == self.params.iterations:
            self.state.run.finished = True

    def run(self):
        while not self.state.run.finished:
            self.step()
            yield self
        self.calculate_metrics()
