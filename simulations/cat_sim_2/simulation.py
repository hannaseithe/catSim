from __future__ import annotations
from dataclasses import asdict, dataclass, field, fields
import json
import logging
import math
from typing import List, Optional, Set, Tuple, TypedDict
from simulations.cat_sim_2.state import (
    ActionType,
    Cat,
    CatMetrics,
    CatTraits,
    Edge,
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
    ActionType.MARK_TERRITORY: {NeedType.TERRITORY: 5, NeedType.TOILET: 4},
    ActionType.GREET_CAT:      {NeedType.SOCIAL: 5, NeedType.TERRITORY: 1},
    ActionType.GROOM_CAT:      {NeedType.SOCIAL: 15, NeedType.TERRITORY: 1},
    ActionType.ATTACK_CAT:     {NeedType.SOCIAL: -10, NeedType.TERRITORY: 25},
    ActionType.GET_PET_BY_HUMAN: {NeedType.SOCIAL: 5},
    ActionType.GO_TOILET:      {NeedType.TOILET: 80},
}

ACTION_LIKELIHOOD: dict[ActionType, float] = {
    ActionType.HUNT: 0.2
}

EDGE_TAX = 1

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

def urgency_score(cat:Cat, need: Tuple[NeedType,float]):
    result = need[1]
    for trait, sm in SCALE_MULTIPLIERS[need[0]].items():
        result += getattr(cat.traits,trait.value) * sm
    return result


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
    mean_aggressive: float = 0.0
    var_aggressive: float = 0.1
    mean_laziness: float = 0.5
    var_laziness: float = 0.05

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
    def __init__(self, params: SimulationParameters):
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
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat, cat_id).value > 1e-9:
                return True
        return False

    def is_home_of_friend(self, node_id: int, cat_id: int) -> bool:
        home_cats = [
            cat.id for cat in self.state.cats.values() if cat.home == node_id
        ]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat, cat_id).value >= -1e-9:
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
        return self.get_relationship(cat1, cat2).value > 1e-9

    def get_enemies_on_node(self, cat:Cat) -> list[int]:
        return [id for id in self.get_cats_on_node(cat.current_node) if self.is_enemy(cat.id, id)]
    
    def is_enemy_here(self, cat: Cat) -> bool:
        return any(
            self.get_relationship(cat.id, other_id).value > 1e-9
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
        return self.get_relationship(cat1, cat2).value < -1e-9

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
        return abs(self.get_relationship(cat1, cat2).value) >= -1e-9 and abs(self.get_relationship(cat1,cat2).value) <= 1e-9

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
                effects[need] += value * cat_attack["probability"]
        if self.seen_neutral(cat, node_id) and node_type in cat_greet["node_type"]:
            for need, value in cat_greet["need_effects"].items():
                effects[need] += value * cat_greet["probability"]
        if self.seen_friendly(cat,node_id) and node_type in cat_groom["node_type"]:
            for need, value in cat_groom["need_effects"].items():
                effects[need] += value * cat_groom["probability"]
        return effects.get(primary_need, 0) * 3 + effects.get(secondary_need, 0)

    def get_relationship(self, cat1: int, cat2: int):
        a, b = sorted((cat1, cat2))
        return self.state.relationships.get((a,b))

    def get_friends(self, cat1: int) -> list [int]:
        result = []
        for rel in self.state.relationships.values():
            if (
                cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2
            ) and rel.value < -1e-9:
                result.append(rel.other_cat(cat1))
        return result

    def get_enemies(self, cat1: int) -> list[int]:
        result = []
        for rel in self.state.relationships.values():
            if (
                cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2
            ) and rel.value > 1e-9:
                result.append(rel.other_cat(cat1))
        return result

    def generate_initial_nodes(self):
        edge_sigma = self.params.var_edges**0.5
        for i in range(self.params.node_amount):
            number_of_edges = max(
                1,
                round(
                    min(
                        random.gauss(self.params.mean_edges, edge_sigma),
                        self.params.node_amount,
                    )
                ),
            )
            self.state.nodes.append(Node(id=i, number_of_edges=number_of_edges))
    
    def generate_initial_edges(self):
        # Minimal connected graph
        available_nodes = [node.id for node in self.state.nodes]
        connected_nodes = [available_nodes.pop(0)]

        while available_nodes:
            n1 = random.choice(connected_nodes)
            n2 = available_nodes.pop(random.randint(0, len(available_nodes) - 1))
            self.state.edges.append(Edge(node1=n1, node2=n2))
            connected_nodes.append(n2)

        # Randomly connected graph
        for node in self.state.nodes:
            edge_partners = self.get_neighboring_nodes(node.id)
            if len(edge_partners) < node.number_of_edges:
                possible_nodes = [i for i in range(self.params.node_amount)]
                possible_nodes.remove(node.id)
                for i in range(node.number_of_edges - len(edge_partners)):
                    rand_node_id = random.choice(possible_nodes)
                    other_node = self.get_node(rand_node_id)
                    if len(self.get_nodes_edges(other_node.id)) < node.number_of_edges:
                        self.state.edges.append(Edge(node1=node.id, node2=rand_node_id))
                    possible_nodes.remove(rand_node_id)

    def generate_initial_cats(self):
        aggressive_sigma = self.params.var_aggressive**0.5
        lazy_sigma = self.params.var_laziness**0.5
        for i in range(self.params.cat_amount):
            available_nodes = [node.id for node in self.state.nodes]
            home_id = random.choice(available_nodes)
            aggressive = max(
                -1, min(1, random.gauss(self.params.mean_aggressive, aggressive_sigma))
            )
            lazy = max(-1, min(1, random.gauss(self.params.mean_laziness, lazy_sigma)))
            self.state.cats.append(
                Cat(
                    CatTraits(
                        id=i,
                        name=f"cat-{i}",
                        home=home_id,
                        aggressive=aggressive,
                        lazy=lazy,
                    )
                )
            )

    def generate_initial_relationships(self):
        available_cats = [cat.traits.id for cat in self.state.cats]
        related_cats = [available_cats.pop(0)]
        while available_cats:
            for cat in available_cats:
                c1 = related_cats[-1]
                c2 = cat
                key = tuple(sorted((c1, c2)))
                self.state.relationships[key] = Relationship(
                    RelationshipTraits(cat1=c1, cat2=c2)
                )
            related_cats.append(available_cats.pop(0))

    def generate_initial_state(self):
        self.generate_initial_nodes()
        self.generate_initial_edges()
        self.generate_initial_cats()
        self.generate_initial_relationships()
        
    def serialize_state(self) -> str:
        return json.dumps(
            fix_tuple_keys_dict(asdict(self.state)), cls=SimulationEncoder
        )
    
    
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

    def identify_primary_needs(self, cat: Cat) -> tuple[NeedType, NeedType]:
        result: list[NeedType] = []
        need_groups: list[list[NeedType]] = [[], [], [], []]
        needs_list: list[tuple[NeedType, float]] = [
            (NeedType(f.name), getattr(cat.needs, f.name))
            for f in fields(cat.needs)
        ]
        first_four = needs_list[:4]
        last_five = sorted(needs_list[4:], key=lambda need: urgency_score(cat, need), reverse=True)
        ordered = first_four + last_five
        for need_type, value in ordered:
            if value < NEED_THRESHOLDS['critical']:
                need_groups[0].append(need_type)
                continue
            if value < NEED_THRESHOLDS['urgent']:
                need_groups[1].append(need_type)
                continue
            if value < NEED_THRESHOLDS['open']:
                need_groups[2].append(need_type)
                continue
            need_groups[3].append(need_type)
        for group in need_groups:
            if len(result) >= 2:
                break
            for need_type in group:
                if len(result) >= 2:
                    break
                result.append(need_type)
        return result[0], result[1]
    
    def get_chosen_node(self, cat: Cat) -> tuple[int | None, int | None]:
        node_scores = []
        primary_need = cat.tick_state.primary_need
        secondary_need = cat.tick_state.secondary_need
        if primary_need is None or secondary_need is None: 
            return None, None
        unknown_adjacent_nodes:Set[int] = set()
        for node_id, m_node in cat.memory.visited_nodes.items():
            node = self.state.nodes[node_id]
            #Identify unknown adjacent nodes
            adjacent_nodes = self.get_neighboring_nodes(node_id)
            for a_node in adjacent_nodes:
                if a_node not in cat.memory.visited_nodes:
                    unknown_adjacent_nodes.add(a_node)
            #Identify possible actions
            possible_actions = []
            possible_actions_for_need = NEED_ACTION_OPTIONS[primary_need]
            for action in possible_actions_for_need:
                if (
                    action in NODE_TYPE_ACTIONS[node.node_type]["available"]
                    or (action in NODE_TYPE_ACTIONS[node.node_type]["conditional"])
                    or (action in NODE_TYPE_ACTIONS[node.node_type]["uncertain"])
                ):
                    possible_actions.append(action)
            if len(possible_actions) == 0:
                node_score = 0.0
                chosen_action = None
                action_score: float = 0.0
            chosen_action = possible_actions[0]
            if len(possible_actions) > 1:
                action_score = 0.0
                for action in possible_actions:
                    if action == ActionType.INVESTIGATE and primary_need == NeedType.EXPLORATION:
                        action_score = ACTION_NEED_EFFECTS[ActionType.INVESTIGATE].get(NeedType.EXPLORATION,0.0) * m_node.novelty_score
                        chosen_action = ActionType.INVESTIGATE
                        continue
                    action_prob = 1.0
                    if action in NODE_TYPE_ACTIONS[node.node_type]["uncertain"]:
                        action_prob = ACTION_LIKELIHOOD[action]
                    if action in NODE_TYPE_ACTIONS[node.node_type]["conditional"]:
                        action_prob = 0
                        if action == "attack_cat" and self.seen_enemy(cat, node_id):
                            action_prob = 0.4
                        if action == "greet_cat" and (self.seen_neutral(cat, node_id) or self.seen_friendly(cat,node_id)):
                            action_prob = 0.6
                        if action == "groom_cat" and self.seen_friendly(cat,node_id):
                            action_prob = 0.4
                    a_s = action_prob * (ACTION_NEED_EFFECTS[action].get(primary_need,0) * 3 + ACTION_NEED_EFFECTS[action].get(secondary_need,0))
                    if a_s > action_score:
                        action_score = a_s
                        chosen_action = action 
            if chosen_action: 
                distance, path = self.memory_distance(cat,node_id)
                node_score = action_score - EDGE_TAX * distance - self.expected_event_effect(cat,node_id,primary_need,secondary_need)
                node_scores.append((node_id,node_score, path[1] if len(path) > 1 else None))
        if primary_need == "exploration":
            for node_id in unknown_adjacent_nodes:
                distance, path = self.memory_distance(cat,node_id)
                node_score = ACTION_NEED_EFFECTS["investigate"].get("exploration",0) - EDGE_TAX * distance
                node_scores.append((node_id, node_score, path[1] if len(path) > 1 else None))
        result = max(node_scores, key=lambda x: x[1])
        return result[0], result[2] 


    def decision_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            # identify primary and secondary need
            cat.tick_state.primary_need, cat.tick_state.secondary_need = self.identify_primary_needs(cat)
            # chose node
            _, next_node = self.get_chosen_node(cat)
            cat.tick_state.will_move_to = next_node

    def movement_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.tick_state.will_move_to is not None:
                cat.current_node = cat.tick_state.will_move_to

    def apply_events(self, node_type: NodeType, cat: Cat) -> None:
        for event in EVENTS.values():
            if node_type in event["node_type"]:
                if random.random() < event["probability"]:
                    for need, value in event["need_effects"].items():
                        setattr(cat.needs,need.value,getattr(cat.needs,need.value) + value)

    def event_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            node = self.get_node(cat.current_node)
            if node is not None:
                self.apply_events(node.node_type, cat)

    def action_step(self) -> None:
        cats_copy = self.state.cats.copy()
        for cat in cats_copy.values():
            if cat.tick_state.will_move_to is not None:
                continue
            if cat.tick_state.primary_need is None or cat.tick_state.secondary_need is None:
                continue
            #figure out action options based on node_type
            available_actions: list[ActionType] = []
            m_node = cat.memory.visited_nodes[cat.current_node]
            if cat.current_node not in cat.memory.visited_nodes:
                available_actions.append(ActionType.INVESTIGATE)
            else:
                node = self.get_node(cat.current_node)

                if node is not None:
                    available_actions.extend(NODE_TYPE_ACTIONS[node.node_type]["available"])
                    if self.is_enemy_here(cat) and ActionType.ATTACK_CAT in NODE_TYPE_ACTIONS[node.node_type]["conditional"]:
                        available_actions.append(ActionType.ATTACK_CAT)
                    if (self.is_neutral_here(cat) or self.is_friend_here(cat)) and ActionType.GREET_CAT in NODE_TYPE_ACTIONS[node.node_type]["conditional"]:
                        available_actions.append(ActionType.GREET_CAT)
                    if self.is_friend_here(cat) and ActionType.GROOM_CAT in NODE_TYPE_ACTIONS[node.node_type]["conditional"]:
                        available_actions.append(ActionType.GROOM_CAT)
                    if ActionType.HUNT in NODE_TYPE_ACTIONS[node.node_type]["uncertain"]:
                        if random.random() > 0.2:
                            available_actions.append(ActionType.HUNT)

            #TODO: chose action based on primary and secondary needs (same formula as in decision_step)
            
            if len(available_actions) == 0:
                action_score: float = 0.0
                chosen_action = None
            else:
                chosen_action = available_actions[0]
                if len(available_actions) > 1:
                    action_score = 0.0
                    for action in available_actions:
                        if action == ActionType.INVESTIGATE and cat.tick_state.primary_need == NeedType.EXPLORATION:
                            action_score = ACTION_NEED_EFFECTS[ActionType.INVESTIGATE].get(NeedType.EXPLORATION,0.0) * m_node.novelty_score
                            chosen_action = ActionType.INVESTIGATE
                            continue
                        a_s = (ACTION_NEED_EFFECTS[action].get(cat.tick_state.primary_need,0) * 3 + ACTION_NEED_EFFECTS[action].get(cat.tick_state.secondary_need,0))
                        if a_s > action_score:
                            action_score = a_s
                            chosen_action = action 
            cat.tick_state.action = chosen_action


            if chosen_action is not None:
                #apply action effects to cat agent
                for need,value in ACTION_NEED_EFFECTS[chosen_action].items():
                    setattr(cat.needs,need.value,getattr(cat.needs,need.value) + value)
                if chosen_action == ActionType.HUNT:
                    if random.random() > (0.6 + cat.traits.strength/100):
                        cat.needs.food += 20

                #apply action effects to cat recipient
                if chosen_action in [ActionType.ATTACK_CAT, ActionType.GREET_CAT, ActionType.GROOM_CAT]:
                        
                    if chosen_action == ActionType.ATTACK_CAT:
                        enemies_on_node = self.get_enemies_on_node(cat)
                        chosen_cat = enemies_on_node[0]
                        rel_value = self.get_relationship(cat.id, chosen_cat).value
                        if len(enemies_on_node) > 1:
                            for enemy in enemies_on_node[1:]:
                                if self.get_relationship(cat.id, enemy).value < rel_value:
                                    chosen_cat = enemy
                                    rel_value = self.get_relationship(cat.id, enemy).value
                        cat.tick_state.other_cat = chosen_cat
                        cat2 = self.get_cat(chosen_cat)

                    if chosen_action == ActionType.GREET_CAT:
                        friends_and_neutrals_on_node = self.get_friends_on_node(cat)
                        friends_and_neutrals_on_node += self.get_neutral_on_node(cat)
                        chosen_cat = random.choice(friends_and_neutrals_on_node)
                        cat.tick_state.other_cat = chosen_cat
                        cat2 = self.get_cat(chosen_cat)

                    if chosen_action == ActionType.GROOM_CAT:
                        friends_on_node = self.get_friends_on_node(cat)
                        chosen_cat = friends_on_node[0]
                        rel_value = self.get_relationship(cat.id, chosen_cat).value
                        if len(friends_on_node) > 1:
                            for friend in friends_on_node[1:]:
                                if self.get_relationship(cat.id, friend).value > rel_value:
                                    chosen_cat = friend
                                    rel_value = self.get_relationship(cat.id, friend).value
                        cat.tick_state.other_cat = chosen_cat
                        cat2 = self.get_cat(chosen_cat)
                        
                    if cat2 is not None:
                        for need, value in INTERACTIVE_EVENTS[chosen_action]["need_effects"].items():
                            setattr(cat2.needs,need.value,getattr(cat2.needs,need.value) + value)
                        rel = self.get_relationship(cat.id, cat2.id)
                        if rel is not None:
                            rel.value += INTERACTIVE_EVENTS[chosen_action]["relationship_effect"]
    


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


    def calculate_metrics(self):
        #TODO: adapt / implement
        G = nx.Graph()

        G.add_nodes_from(range(self.params.node_amount))

        self.set_relationship_metrics(G)

        cliques = [clique for clique in list(nx.find_cliques(G)) if len(clique) > 2]
        self.set_cat_metrics(cliques)
        self.set_simulation_metrics(cliques)

    def step(self):
        self.decision_step()
        self.movement_step()
        self.event_step()
        self.action_step()
        self.memory_update_step()
        self.drain_step()
        self.set_stats_step()
        self.state.run.tick += 1
        if self.state.run.tick == self.params.iterations:
            self.state.run.finished = True

    def run(self):
        while not self.state.run.finished:
            self.step()
            yield self
        self.calculate_metrics()
