from dataclasses import asdict
from simulation.simulation import Simulation


def extract_metrics(sim:Simulation):
     
    cat_metrics = [{'id': cat.traits.id, 'traits': asdict(cat.traits), **(asdict(cat.metrics) if cat.metrics else {})} for cat in sim.cats]
    rel_metrics = [{'key':(rel.traits.cat1,rel.traits.cat2),'value':rel.value,**(asdict(rel.metrics) if rel.metrics else {})} for rel in sim.relationships.values()]
    sim_metrics = asdict(sim.metrics) if sim.metrics else {}

    return {
        'cats': cat_metrics,
        'relationships': rel_metrics,
        'simulation': sim_metrics
    }

