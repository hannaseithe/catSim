from simulations.cat_sim_2.simulation import Simulation, SimulationParameters
from simulations.cat_sim_2.state import NeedType

params = SimulationParameters(iterations=10000, cat_amount=10, node_amount=100)
sim = Simulation(params)
sim.generate_initial_state()

print(f"Nodes: {len(sim.state.nodes)}, Edges: {len(sim.state.edges)}, Cats: {len(sim.state.cats)}")
for cat in sim.state.cats.values():
    t = cat.traits
    print(f"  {cat.name}: aggr={t.aggression:+.1f}  conf={t.confidence:+.1f}  curi={t.curiosity:+.1f}  actv={t.activeness:+.1f}  str={t.strength:+.1f}")
print()
print(f"{'Tick':>5} | {'Cat':<8} | {'Node':>5} | {'Hlth':>6} | {'Food':>6} | {'Toil':>6} | {'Enrg':>6} | {'Socl':>6} | {'Hunt':>6} | {'Expl':>6} | {'Terr':>6} | {'Hygn':>6} | {'Mem':>4} | {'Primary':<12} | Action")
print("-" * 135)

cats_to_log = list(sim.state.cats.values())

for state in sim.run():
    tick = state.state.run.tick
    if tick % 100 == 0:
        for cat in cats_to_log:
            cat = state.state.cats[cat.id]
            action  = cat.tick_state.action.value if cat.tick_state.action else "-"
            primary = cat.tick_state.primary_need.value if cat.tick_state.primary_need else "-"
            mem     = len(cat.memory.visited_nodes)
            n = cat.needs
            print(f"{tick:>5} | {cat.name:<8} | {cat.current_node:>5} | {n[NeedType.HEALTH]:>6.1f} | {n[NeedType.FOOD]:>6.1f} | {n[NeedType.TOILET]:>6.1f} | {n[NeedType.ENERGY]:>6.1f} | {n[NeedType.SOCIAL]:>6.1f} | {n[NeedType.HUNT]:>6.1f} | {n[NeedType.EXPLORATION]:>6.1f} | {n[NeedType.TERRITORY]:>6.1f} | {n[NeedType.HYGIENE]:>6.1f} | {mem:>4} | {primary:<12} | {action}")
        print()

m = sim.metrics
assert m is not None
print("=== Simulation Metrics ===")
print(f"Friend groups: {m.friendgroups_total} (avg size {m.average_size_friendgroups:.1f}, largest {m.largest_group_size})")
print(f"Isolated cats: {m.isolated_cats_count}")
print(f"Mean relationship value (interacted pairs): {m.mean_relationship_value:.2f}")
print(f"Interaction density: {m.interaction_density:.3f}")
print()

print("=== Cat Metrics ===")
for cat in cats_to_log:
    cat = sim.state.cats[cat.id]
    cm = cat.metrics
    assert cm is not None
    node_share = ", ".join(f"{getattr(k, 'value', k)}={v:.2f}" for k, v in cm.time_share_by_node_type.items())
    action_share = ", ".join(f"{getattr(k, 'value', k) or 'none'}={v:.2f}" for k, v in cm.time_share_by_action.items())
    print(f"{cat.name}: exploration={cm.exploration_index:.2f}  interacted_with={cm.num_cats_interacted_with}  friendgroups={cm.amount_friendgroups} (avg size {cm.average_size_friendgroup:.1f})")
    print(f"    time by node: {node_share}")
    print(f"    time by action: {action_share}")

print()
print("Done.")
