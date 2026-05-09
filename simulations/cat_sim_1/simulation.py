from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
import logging
import math
from typing import Optional
from simulations.cat_sim_1.state import (
    Cat,
    CatMetrics,
    CatTraits,
    Edge,
    Node,
    Relationship,
    RelationshipMetrics,
    RelationshipTraits,
)
import random
import networkx as nx

from simulations.cat_sim_1.utils import validate_dict

logger = logging.getLogger(__name__)

lazy_weight = 0.1
relationship_weight = 0.2


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
    cats: list[Cat] = field(default_factory=list)
    relationships: dict[tuple[int, int], Relationship] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    run: SimulationIter = field(default_factory=SimulationIter)
    stats: SimulationStats = field(default_factory=SimulationStats)

    @classmethod
    def from_dict(cls, data: dict) -> SimulationState:
        validate_dict(data, cls)
        return SimulationState(
            cats=[Cat.from_dict(s_cat) for s_cat in data["cats"]],
            relationships={
                Relationship.parse_key(key): Relationship.from_dict(s_rel)
                for key, s_rel in data["relationships"].items()
            },
            edges=[Edge.from_dict(s_edge) for s_edge in data["edges"]],
            nodes=[Node.from_dict(s_node) for s_node in data["nodes"]],
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
        for node in self.state.nodes:
            if node.id == node_id:
                return node
        return None

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
            cat.traits.id for cat in self.state.cats if cat.traits.home == node_id
        ]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat, cat_id).value > 1e-9:
                return True
        return False

    def is_home_of_friend(self, node_id: int, cat_id: int) -> bool:
        home_cats = [
            cat.traits.id for cat in self.state.cats if cat.traits.home == node_id
        ]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat, cat_id).value >= -1e-9:
                return True
        return False

    def is_neutral_node(self, node_id: int) -> bool:
        home_cats = [
            cat.traits.id for cat in self.state.cats if cat.traits.home == node_id
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
        for cat in self.state.cats:
            if cat.traits.id == cat_id:
                return cat
        return None

    def get_cats_on_node(self, node_id: int) -> list[int]:
        result = []
        for cat in self.state.cats:
            if cat.current_node == node_id:
                result.append(cat.traits.id)
        return result

    def get_relationship(self, cat1, cat2):
        key = tuple(sorted((cat1, cat2)))
        return self.state.relationships.get(key)

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
    
    def get_probs_for_neighboring_nodes(self, cat: Cat) -> dict[int, float]:
        assert cat.current_node is not None
        neighboring_nodes = self.get_neighboring_nodes_no_enemy(
            cat.current_node, cat.traits.id
        )
        probs = {node: 0.0 for node in neighboring_nodes}
        for node_id in neighboring_nodes:
            cats_at_node = self.get_cats_on_node(node_id)
            probs[node_id] = (1 - cat.traits.lazy) * (1 - lazy_weight)
            for other_cat in cats_at_node:
                relationship = self.get_relationship(cat.traits.id, other_cat)
                probs[node_id] += (
                    cat.traits.aggressive
                    * relationship.value
                    * relationship_weight
                )
            probs[node_id] *= random.uniform(0.9, 1.1)
            probs[node_id] = max(1e-9, min(probs[node_id], 1))
        return probs
    
    def get_prob_to_stay(self, cat: Cat) -> float:
        assert cat.current_node is not None
        if cat.needs_to_run:
            prob_to_stay = 0.0
            cat.needs_to_run = False
        else:
            prob_to_stay = cat.traits.lazy * lazy_weight
            cats_at_node = self.get_cats_on_node(cat.current_node)
            cats_at_node.remove(cat.traits.id)
            for other_cat in cats_at_node:
                relationship = self.get_relationship(cat.traits.id, other_cat)
                prob_to_stay += (
                    cat.traits.aggressive
                    * relationship.value
                    * relationship_weight
                )
            prob_to_stay *= random.uniform(0.9, 1.1)
            prob_to_stay = max(1e-9, min(prob_to_stay, 1))
        return prob_to_stay
    
    def make_choice(self, probs: dict[int,float], prob_to_stay: float) -> str | int:
        choices = list(probs.keys()) + ["stay"]
        weights = list(probs.values()) + [prob_to_stay]
        if len(choices) == 1:
            choice = choices[0]
        else:
            choice = random.choices(choices, weights=weights, k=1)[0]
        return choice
    
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

    def get_possible_pairs(self, cats_on_node: list[Cat]) -> list[tuple[float, int, int]]:
        possible_pairs = []
        for index1, cat1 in enumerate(cats_on_node):
            for index2 in range(index1 + 1, len(cats_on_node)):
                cat2 = cats_on_node[index2]

                rel = self.get_relationship(cat1.traits.id, cat2.traits.id)
                mutual_intent = (
                    cat1.traits.aggressive * rel.value
                    + cat2.traits.aggressive * rel.value
                    + random.uniform(-0.3, 0.3)
                )
                if mutual_intent > 0.2:
                    possible_pairs.append(
                        (mutual_intent, cat1.traits.id, cat2.traits.id)
                    )
        return possible_pairs
    
    def pair_up_cats(self, possible_pairs: list[tuple[float, int, int]]) -> tuple[list[tuple[int,int]],set[int]]:
        engaged = set()
        paired_cats = []
        for _, i, j in possible_pairs:
            if i not in engaged and j not in engaged:
                engaged.add(i)
                engaged.add(j)
                paired_cats.append((i, j))
        return (paired_cats, engaged)

    def set_general_engagement_stats(self, rel: Relationship) -> None:
        rel.stats.absolute_delta += 0.05
        self.state.stats.total_number_interactions += 1
        rel.stats.interacted = True
        if abs(rel.value) < 1e-9:
            rel.stats.number_of_sign_flips += 1

    def set_fight_stats(self, cat1: Cat, cat2: Cat, rel: Relationship) -> None:
        cat1.stats.fights += 1
        cat1.stats.interacted_with.add(cat2.traits.id)
        cat2.stats.fights += 1
        cat2.stats.interacted_with.add(cat1.traits.id)
        if rel.value > rel.stats.max_value:
            rel.stats.max_value = rel.value

    def set_friendly_engagement_stats(self, cat1: Cat, cat2: Cat, rel: Relationship) -> None:
        cat1.stats.friendly_interaction += 1
        cat1.stats.interacted_with.add(cat2.traits.id)
        cat2.stats.friendly_interaction += 1
        cat2.stats.interacted_with.add(cat1.traits.id)
        if rel.value < rel.stats.min_value:
            rel.stats.min_value = rel.value

    def set_relationship_metrics(self, G):
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

    def movement_step(self) -> None :
        cats_copy = self.state.cats.copy()
        for cat in cats_copy:
            if not cat.is_on_the_edge():

                probs_nodes = self.get_probs_for_neighboring_nodes(cat)   
                prob_to_stay = self.get_prob_to_stay(cat)
                choice = self.make_choice(probs_nodes,prob_to_stay)
                self.set_stats_at_node(cat, choice)
                if choice != "stay":
                    cat.leave(choice)
            else:
                cat.arrive()
                cat.stats.iter_on_edge += 1

    def engagement_step(self):
        for node in self.state.nodes:
            engaged = set()
            cats_on_node = [self.get_cat(cat) for cat in self.get_cats_on_node(node.id)]

            if len(cats_on_node) > 1:

                possible_pairs = self.get_possible_pairs(cats_on_node)

                possible_pairs.sort(reverse=True)

                paired_cats, engaged = self.pair_up_cats(possible_pairs)

                for pair in paired_cats:

                    c1, c2 = pair
                    cat1 = self.get_cat(c1)
                    cat2 = self.get_cat(c2)
                    rel = self.get_relationship(c1, c2)

                    interaction_value = (
                        cat1.traits.aggressive + cat2.traits.aggressive + rel.value
                    )

                    self.set_general_engagement_stats(rel)
                    
                    if interaction_value > 0:
                        #engage in fight
                        if cat1.traits.aggressive > cat2.traits.aggressive:
                            cat2.needs_to_run = True
                        else:
                            cat1.needs_to_run = True
                        rel.value += 0.05
                        rel.value = min(1, rel.value)
                        self.set_fight_stats(cat1, cat2, rel)

                    else:
                        #engage in friendly interaction
                        rel.value -= 0.05
                        rel.value = max(-1, rel.value)
                        self.set_friendly_engagement_stats(cat1, cat2, rel)

            for cat in cats_on_node:
                if not engaged or cat.traits.id not in engaged:
                    cat.stats.sleeps += 1

    def calculate_metrics(self):
        G = nx.Graph()

        G.add_nodes_from(range(self.params.node_amount))

        self.set_relationship_metrics(G)

        cliques = [clique for clique in list(nx.find_cliques(G)) if len(clique) > 2]
        self.set_cat_metrics(cliques)
        self.set_simulation_metrics(cliques)

    def step(self):
        self.movement_step()
        self.engagement_step()
        self.state.run.tick += 1
        if self.state.run.tick == self.params.iterations:
            self.state.run.finished = True

    def run(self):
        while not self.state.run.finished:
            self.step()
            yield self
        self.calculate_metrics()
