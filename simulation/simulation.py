from dataclasses import dataclass
from typing import Optional
from simulation.state import Cat, CatMetrics, CatTraits, Edge, Node, Relationship, RelationshipMetrics, RelationshipTraits
import random
import networkx as nx

lazy_weight=0.1
relationship_weight=0.2

@dataclass
class SimulationMetrics:
    friendgroups_total: int
    average_size_friendgroups: int


@dataclass(frozen=True)
class SimulationParameters:
    iterations: int
    seed: int
    cat_amount: int
    node_amount: int
    mean_edges: int
    var_edges:float
    mean_aggressive: float
    var_aggressive: float
    mean_laziness:float
    var_laziness:float

    def __post_init__(self):
        if self.iterations <= 0:
            raise ValueError("iterations must be greater than 0")

class Simulation:
    def __init__(self, params: SimulationParameters):
        self.params = params

        random.seed(self.params.seed)

        self.cats: list[Cat] = []
        self.relationships: dict[tuple[int, int], Relationship] = {}
        self.edges: list[Edge] = []
        self.nodes: list[Node] = []

        self.metrics: Optional[SimulationMetrics] = None

    def get_node(self, node_id: int):
        for node in self.nodes:
            if node.id == node_id:
                return node

    def get_nodes_edges(self,node_id:int):
        result = []
        for edge in self.edges:
            if edge.node_in_edge(node_id):
                result.append(edge)
        return result
    
    def get_nodes_edge_partners(self, node_id):
        result = []
        for edge in self.edges:
            if edge.node_in_edge(node_id):
                result.append(edge.other_node(node_id))
        return result
    
    def what_node_is_cat_at(self,cat):
        cat.current_node
    
    def is_home_of_enemy(self, node_id, cat_id):
        home_cats = [cat.traits.id for cat in self.cats if cat.traits.home == node_id]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat,cat_id).value > 0:
                return True
        return False
    
    def is_home_of_friend(self, node_id, cat_id):
        home_cats = [cat.traits.id for cat in self.cats if cat.traits.home == node_id]
        for cat in home_cats:
            if cat == cat_id:
                return False
            if self.get_relationship(cat,cat_id).value >= 0:
                return True
        return False
    
    def is_neutral_node(self, node_id, cat_id):
        home_cats = [cat.traits.id for cat in self.cats if cat.traits.home == node_id]
        return len(home_cats) == 0
    

    def get_nodes_edge_partners_no_enemy_home(self, node_id, cat_id):
        result = self.get_nodes_edge_partners(node_id)
        result_copy = result.copy()
        for node in result_copy:
            if self.is_home_of_enemy(node,cat_id):
                result.remove(node)
        return result
    
    def get_cat(self, cat_id):
        for cat in self.cats:
            if cat.traits.id == cat_id:
                return cat
    
    def get_cats_on_node(self, node_id):
        result = []
        for cat in self.cats:
            if cat.current_node == node_id:
                result.append(cat.traits.id)
        return result
    
    def get_relationship(self, cat1, cat2):
        key = tuple(sorted((cat1, cat2)))
        return self.relationships.get(key)
    
    def get_friends(self,cat1):
        result = []
        for rel in self.relationships.values():
            if (cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2) and rel.value < 0:
                result.append(rel.other_cat(cat1))
        return result
    
    def get_enemies(self,cat1):
        result = []
        for rel in self.relationships.values():
            if (cat1 == rel.traits.cat1 or cat1 == rel.traits.cat2) and rel.value > 0:
                result.append(rel.other_cat(cat1))
        return result


    def generate_initial_state(self):

        #Nodes
        edge_sigma = self.params.var_edges ** 0.5
        for i in range(self.params.node_amount):
            number_of_edges = max(1,round(random.gauss(self.params.mean_edges, edge_sigma)))
            self.nodes.append(Node(id=i, number_of_edges=number_of_edges))

        
        #Minimal connected graph
        available_nodes = [node.id for node in self.nodes]
        connected_nodes = [available_nodes.pop(0)]

        while available_nodes:
            n1 = random.choice(connected_nodes)
            n2 = available_nodes.pop(random.randint(0, len(available_nodes) - 1))
            self.edges.append(Edge(node1=n1,node2=n2))
            connected_nodes.append(n2)

        #Randomly connected graph
        for node in self.nodes:
            edge_partners = self.get_nodes_edge_partners(node.id)
            if len(edge_partners) < number_of_edges:
                possible_nodes = [i for i in range(self.params.node_amount)]
                possible_nodes.remove(node.id)
                for i in range(node.number_of_edges - len(edge_partners)):
                    rand_node_id = random.choice(possible_nodes)
                    other_node = self.get_node(rand_node_id)
                    if len(self.get_nodes_edges(other_node.id)) < node.number_of_edges:
                        self.edges.append(Edge(node1=node.id,node2=rand_node_id))
                    possible_nodes.remove(rand_node_id)

        #Cats
        aggressive_sigma = self.params.var_aggressive ** 0.5
        lazy_sigma = self.params.var_laziness ** 0.5
        for i in range(self.params.cat_amount):
            available_nodes= [node.id for node in self.nodes]
            home_id = random.choice(available_nodes)
            aggressive = max(-1,min(1,random.gauss(self.params.mean_aggressive, aggressive_sigma)))
            lazy = max(-1,min(1,random.gauss(self.params.mean_laziness, lazy_sigma)))
            self.cats.append(Cat(CatTraits(id=i,name=f"cat-{i}",home=home_id, aggressive=aggressive,lazy=lazy)))

        #Relationships  
        available_cats = [cat.traits.id for cat in self.cats]
        related_cats = [available_cats.pop(0)]
        while available_cats:
            for cat in available_cats:
                c1 = related_cats[-1]
                c2 = cat
                key = tuple(sorted((c1, c2)))
                self.relationships[key] = Relationship(
                    RelationshipTraits(cat1=c1,cat2=c2)
                )
            related_cats.append(available_cats.pop(0))

    def movement_step(self):
        new_cats = self.cats.copy()
        for cat in new_cats:
            if not cat.is_on_the_edge():
                edge_partners = self.get_nodes_edge_partners_no_enemy_home(cat.current_node, cat.traits.id)
                probs = {node: 0.0 for node in edge_partners}
                for node_id in edge_partners:
                    cats_at_node = self.get_cats_on_node(node_id)
                    probs[node_id] = ((1-cat.traits.lazy) *(1-lazy_weight))
                    for other_cat in cats_at_node:
                        relationship = self.get_relationship(cat.traits.id,other_cat)
                        probs[node_id] += cat.traits.aggressive*relationship.value *relationship_weight
                    probs[node_id] *= random.uniform(0.9, 1.1)
                    probs[node_id] = max(0, min(probs[node_id],1))
                if cat.needs_to_run: 
                    prob_to_stay = 0.0
                else: 
                    prob_to_stay = (cat.traits.lazy *lazy_weight)
                    cats_at_node = self.get_cats_on_node(cat.current_node)
                    cats_at_node.remove(cat.traits.id)
                    for other_cat in cats_at_node:
                        relationship = self.get_relationship(cat.traits.id,other_cat)
                        prob_to_stay += cat.traits.aggressive*relationship.value *relationship_weight
                    prob_to_stay *= random.uniform(0.9, 1.1)
                    prob_to_stay = max(0, min(prob_to_stay,1))

                #chose action    
                choices = list(probs.keys()) + ["stay"]
                weights = list(probs.values()) + [prob_to_stay]
                if len(choices) == 1:
                    source = choices[0]
                else:
                    source = random.choices(choices, weights=weights, k=1)[0]

                #set stats for cats at nodes
                cat.time_at_current_node += 1
                if cat.is_at_home():
                    cat.stats.iter_at_home += 1
                    if not source == "stay":
                        cat.stats.times_at_home +=1
                elif self.is_neutral_node(cat.current_node,cat.traits.id):
                    cat.stats.iter_at_neutral += 1
                    if not source == "stay":
                        cat.stats.times_at_neutral +=1
                else:
                    cat.stats.iter_at_friendly += 1
                    if not source == "stay":
                        cat.stats.times_at_friendly +=1

                if source == "stay":
                    pass
                else:
                    cat.leave(source)
            else:
                cat.arrive()
                cat.stats.iter_on_edge += 1
                
            cat.needs_to_run=False

    def engagement_step(self):
        result = []
        for node in self.nodes:
            cats_on_node = [self.get_cat(cat) for cat in self.get_cats_on_node(node.id)]
            engaged = set()
            n = len(cats_on_node)
            if n > 1: 
                possible_pairs= []
                for index1, cat1 in enumerate(cats_on_node):
                    for index2 in range(index1 + 1, n):

                        cat2= cats_on_node[index2]
        
                        rel = self.get_relationship(cat1.traits.id,cat2.traits.id)
                        mutual_intent = cat1.traits.aggressive * rel.value + cat2.traits.aggressive * rel.value + random.uniform(-0.3, 0.3)
                        if mutual_intent > 0.2:
                            possible_pairs.append((mutual_intent, cat1.traits.id,cat2.traits.id))
                possible_pairs.sort(reverse=True)

                

                for _, i, j in possible_pairs:
                    if i not in engaged and j not in engaged:
                        engaged.add(i)
                        engaged.add(j)
                        result.append((i, j))

            for cat in cats_on_node:
                if cat not in engaged:
                    cat.stats.sleeps += 1

        for pair in result:
            c1,c2 = pair
            cat1 = self.get_cat(c1)
            cat2 = self.get_cat(c2)
            rel = self.get_relationship(c1,c2)


            interaction_value = cat1.traits.aggressive + cat2.traits.aggressive + rel.value
            rel.stats.absolute_delta += 0.05
            if interaction_value > 0:
                cat1.stats.fights += 1
                cat1.stats.interacted_with.add(c2)
                cat2.stats.fights += 1
                cat2.stats.interacted_with.add(c1)
                if cat1.traits.aggressive > cat2.traits.aggressive:
                    cat2.needs_to_run = True
                else:
                    cat1.needs_to_run = True
                rel.value += 0.05
                rel.value = min(1,rel.value)
            else:
                cat1.stats.friendly_interaction += 1
                cat1.stats.interacted_with.add(c2)
                cat2.stats.friendly_interaction += 1
                cat2.stats.interacted_with.add(c1)
                rel.value -= 0.05
                rel.value = max(-1,rel.value)


    def calculate_metrics(self):


            G = nx.Graph()

            G.add_nodes_from(range(70))
            for rel in self.relationships.values():
                rel.metrics = RelationshipMetrics(1 - (rel.stats.absolute_delta/self.params.iterations))
                if rel.value < 0:
                    G.add_edge(rel.traits.cat1,rel.traits.cat2)

            cliques = [clique for clique in list(nx.find_cliques(G)) if len(clique) > 2]

            for cat in self.cats:
                config = {
                    'percent_time_spent_home' : cat.stats.iter_at_home / self.params.iterations,
                    'percent_time_spent_on_edge' : cat.stats.iter_on_edge / self.params.iterations,
                    'percent_time_spent_on_neutral_ground' : cat.stats.iter_at_neutral/ self.params.iterations,
                    'percent_time_spent_at_friends_house' : cat.stats.iter_at_friendly / self.params.iterations,
                    'average_iter_spent_at_home' : cat.stats.iter_at_home / cat.stats.times_at_home if cat.stats.times_at_home > 0 else 0,
                    'average_iter_spent_at_friends_home' : cat.stats.iter_at_friendly / cat.stats.times_at_friendly if cat.stats.times_at_friendly > 0 else 0,
                    'average_iter_spent_on_neutral_node' : cat.stats.iter_at_neutral / cat.stats.times_at_neutral if cat.stats.times_at_neutral > 0 else 0,
                    'amount_of_cats_interacted_with' : len(cat.stats.interacted_with),
                    'amount_of_friends' : len(self.get_friends(cat.traits.id)),
                    'amount_of_enemies' : len(self.get_enemies(cat.traits.id)),
                    'percent_time_spent_fighting' : cat.stats.fights /self.params.iterations,
                    'percent_time_spent_friendly_interaction' : cat.stats.friendly_interaction / self.params.iterations,
                    'percent_time_spent_sleeping' : cat.stats.sleeps / self.params.iterations
                }
                

                cats_cliques = [clique for clique in cliques if cat.traits.id in clique]

                config['amount_friendgroups'] = len(cats_cliques)



                config['average_size_friendgroup'] = 0 if len(cats_cliques) == 0 else  sum([len(clique) for clique in cats_cliques]) / config['amount_friendgroups']
                cat.metrics = CatMetrics(**config)
                    
            average_size_friendgroups = 0 if len(cliques) == 0 else sum([len(clique) for clique in cliques])  / len(cliques)      
            self.metrics = SimulationMetrics(len(cliques),average_size_friendgroups)


    def run(self):

        for i in range(self.params.iterations):
            
            self.movement_step()
            self.engagement_step()

        self.calculate_metrics()

