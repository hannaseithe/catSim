## General

- Generator pattern with `run` method (same as cat_sim_1)
- `from_dict` / `to_dict` serialization and validation pattern (same as cat_sim_1)

## Simulation Phases (per tick)

1. **Decision** — each cat scores all candidate nodes and decides: move or act
2. **Movement** — moving cats traverse one edge
3. **Event** — probabilistic events fire per cat at their current node
4. **Action** — stationary cats execute their chosen action
5. **Memory update** — cats update their memory maps
6. **Drain** — need drain rates applied to all cats

## State Classes

### Node
- Drop `number_of_edges` from cat_sim_1 — it was only a graph generation parameter, not a real node property
- Fields: `id`, `node_type`: Street | House | Garden/Woods

### Edge
- Fields: `node1`, `node2` (same as cat_sim_1)

### MemoryNode (inherits Node)
- `id`, `node_type` (from Node)
- `last_seen_cats`: list of cat ids present on last visit — persists indefinitely until updated
- `novelty_score`: float

### MemoryEdge (inherits Edge)
- `node1`, `node2` (from Edge)
- No additional fields needed

### CatMemory
- Collection of `MemoryNode` objects
- Collection of `MemoryEdge` objects
- Append-only: nodes and edges are never removed once discovered
- A cat learns a node and all its edges on arrival

## Pathfinding

- Algorithm: BFS (Breadth-First Search) on the cat's personal memory map
- Run once per cat per tick to get shortest distance to every known node
- O(nodes + edges) — fast even for large memory maps
- Distance feeds into edge tax calculation: `node score = need satisfaction value - (edge tax × distance)`
- Unvisited adjacent nodes (known via edges but never visited) are always added as candidates with score: `first_time_exploration - edge tax × distance`

## Decision Phase

- Cat scores all known nodes + adjacent unvisited nodes
- Highest scoring node wins
- If winner = current node → cat acts this tick
- If winner = other node → cat moves one edge in that direction this tick (BFS determines which adjacent node to move to)

## Memory Update Phase

On arriving at a node, cat updates:
- Adds node to memory (if new): type, initial novelty score
- Adds all edges connecting to that node (if new)
- Updates `last_seen_cats` with cats currently present
- Adjusts novelty score: simple visit = small decrease, `investigate` action = larger decrease, absence over time = increase
