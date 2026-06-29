## Needs

### Need level
- 100 - fully satisfied
- 0 - completely depleted

### Needs and their priorities
1. First priority:
    - Health
        - Incapacitation Flag (when cat hits zero): cat goes home, out of action, very slow recovery

2. Second priority:
    - Food
        - Incapacitation Flag (when cat hits zero): cat goes home, out of action, very slow recovery

3. Third priority:
    - Toilet

4. Fourth priority:
    - Energy

5. Fifth priority:
    - Social
    - Hunt/Play
    - Exploration
    - Territory
    - Hygiene

### Needs threshholds
- Satisfied — don't pursue : 100 - 90
- Open — would satisfy if opportunity arises: 90 - 30
- Urgent — actively seek to satisfy: 30 - 10
- Critical — overrides most other needs: 10 - 0 

### Needs threshold depletion multipliers

#### Health
- Does not drain by itself over time, but drains depending on certain actions or events (see below)

#### Food
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -1.7 |
| Open | 90-30 | -1.4 |
| Urgent | 30-10 | -0.04 |
| Critical | 10-0 | -0.004 |

#### Toilet
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -0.12 |
| Open | 90-30 | -6.67 |
| Urgent | 30-10 | -8.33 |
| Critical | 10-0 | -16.67 |

#### Energy
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -10 |
| Open | 90-30 | -0.63 |
| Urgent | 30-10 | -0.1 |
| Critical | 10-0 | -0.017 |

#### Social
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -0.069 |
| Open | 90-30 | -0.104 |
| Urgent | 30-10 | -0.017 |
| Critical | 10-0 | -0.005 |

#### Hunt/Play
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -2.5 |
| Open | 90-30 | -0.83 |
| Urgent | 30-10 | -0.83 |
| Critical | 10-0 | -0.012 |

#### Exploration
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -0.035 |
| Open | 90-30 | -0.042 |
| Urgent | 30-10 | -0.009 |
| Critical | 10-0 | -0.002 |

#### Territory
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -0.83 |
| Open | 90-30 | -1.67 |
| Urgent | 30-10 | -0.083 |
| Critical | 10-0 | -0.017 |

#### Hygiene
| Threshold | Range | Drain rate (pts/tick) |
|-----------|-------|----------------------|
| Satisfied | 100-90 | -1.67 |
| Open | 90-30 | -0.21 |
| Urgent | 30-10 | -0.035 |
| Critical | 10-0 | -0.005 |


### Needs prioritization
1. Threshold level — Critical beats Urgent beats Open beats Satisfied
2. Within same threshold — fixed priority ordering first (Health before Food before Energy etc.)
3. Same threshold AND same priority — continuous urgency score (level + trait level x scale multiplier) as final tiebreaker

### Need incapacitation Flag
When a cat reaches zero for food or health it is incapacitated for 2016 ticks (7 days), after which it moves up to critical starts normal replenishing. Basically a divine intervention from the evil vet god


## Traits
### List of traits
- Aggression (aggressive ↔ friendly)
- Confidence (confident ↔ fearful)
- Curiosity (curious ↔ incurious)
- Activeness (active ↔ lazy)
- Strength (strong ↔ weak)

### Level encoding
- Symmetric around zero: 10 to -10

### Strength
Only affects fight outcomes (see Events → Cat attack). Does not modulate need urgency or action choice.

### Modulate multiplier for urgency score (see Needs prioritization #3)
Formula: Need level + trait level x scale multiplier
- Curiosity modulates:
    - Exploration need with SM: 2
- Aggression modulates:
    - Territory need with SM: +2
    - Social need with SM: -2
- Confidence modulates:
    - Exploration need with SM: 2
    - Hunt/Play need with SM: 2
    - Social need with SM: 2
    - Territory need with SM: 2

### Modulate the edge tax
- Activeness modulates:
    - formula: base edge tax - ((activeness + 10) / 20) × SM

### Modulate event probability
- confidence assumes higher probabilities for negative events


## Movement

### Movement Choice
To decide, a cat scores all known nodes (including its current one) and picks the highest scoring node:

Each tick a cat makes one decision: **move** to an adjacent node, or **act** at its current node. A cat cannot do both in the same tick.

A cat moves to(wards) the node which can satisfy its needs best. There is a `edge tax` - the more edges we have to cross to get to the node, the higher is the tax (additive). The node with the highest node score wins.
- node score = need satisfaction value - (edge tax × distance)
- need satisfaction value: weighted sum across all needs (how will the needs be affected at this node?), primary need gets highest weight
    -formula: planned action effects on needs (where highest priority need gets higher weight multiplier and maybe second highes too)+ event-effect on need * probability (if even has no fixed probability, but depends on actions of another cat, probability is assumed to be 0.1) 

Each tick a cat makes one decision: **move** to an adjacent node, or **act** at its current node — not both.
- If the highest scoring node is the current node → cat acts there this tick
- If the highest scoring node is a different node → cat moves one edge in that direction this tick (no action)


### Pathfinding & Spatial Memory
- A cat has an internal memory map of nodes it has visited — append-only, never forgotten
- Unvisited nodes do not exist in the cat's decision space
- New nodes are discovered by physically moving to an adjacent unvisited node
- Each known node stores:
    - **Last seen cats**: which cats were present on last visit — persists indefinitely until updated by a new visit
    - **Novelty score**: familiarity with the node (see below)
- Movement decisions only consider nodes in the cat's memory map
- Remembered cats feed into node scoring:
    - Nodes with remembered friendly cats: `greet cat` and `play with/groom cat` count towards the node's need satisfaction value
    - Nodes with remembered enemy cats: `attack cat` counts towards the node's need satisfaction value

#### Novelty Score
- Represents how familiar a cat is with a node
- Increases over time (absence makes the node feel novel again)
- Decreases on a simple visit
- Decreases more on `investigate`
- Used as a multiplier for the `investigate` action's Exploration effect: `exploration: +20 × novelty score`
- `investigate` is only available if novelty score > threshold

### Exploring
- Adjacent unvisited nodes are always added as candidates to the movement decision
- An unvisited node has a fixed `first_time_exploration` value towards Exploration need (higher than `investigate`), so its score is: `first_time_exploration - edge tax × distance`
- Whether an unknown node wins depends on how high the Exploration need is relative to other needs
- If multiple unknown adjacent nodes are candidates, one is chosen at random

## Actions
Performing an action means the cat stays at its current node that tick (no movement).
### Action Types
- sleep/rest
    - need effects:
        - Health: +0.5
        - Energy: +1.5
- eat
    - need effects:
        - food: +40
- hunt
    - need effects:
        - energy: -5
        - hunt: +20
- investigate
    - need effects:
        - exploration: +20 (*novelty score of node)
- play
    - need effects:
        - hunt: +10
        - energy: -4
- groom
    - need effects:
        -hygiene: +10
        - health: +0.2
- mark territory 
    - need effects: 
        - territory: +5
        - toilet: +4
- greet cat
    - need effects:
        - social: +5
        - territory: +1
- play with/groom cat
    - need effects:
        - social: +15
        - territory: +1
- attack cat
    - need effects:
        - social: -10
        - territory: +25
- get pet by human
    - need effects:
        - social: +5
- go to toilet
    - need effects:
        - toilet: +80



## Nodes
### Node Types

#### Street
- Available actions: investigate, mark territory
- No passive effects (risk covered by events)

#### House
- each cat "owns" one house (1:many house:cats)
- Available actions: sleep/rest, eat, groom, play, investigate, get pet by human, go to toilet
- Conditional actions: greet cat, play with/groom cat, attack cat — only if another cat that lives in this house is present
- Not available: hunt, mark territory
- Passive effects: Health: +0.1/tick

#### Garden/Woods
- Available actions: sleep/rest, hunt, investigate, play, groom, mark territory, greet cat, play with/groom cat, attack cat, go to toilet
- Not available: eat, get pet by human


## Events
Are probabilistic or deterministic (actions by other cats, which have a fixed assumed probability used for movement choice) events that happen to the cat, which it did not chose itself. Events fire at the node a cat arrives at (moving cats) or at the current node (stationary cats).

### Event Types
- Cat attack
    - Node: Garden/Woods 
    - Assumed Probability: 0.1 If node is associated with enemy cat
    - Need effects on defender:
        - Health: -10 + (attacker Strength - defender Strength) × SM
        - Social: -5
        - Territory: -5
        - Hygiene: -5
        - Energy: -10
    - Need effects on attacker:
        - Health: -3 + (defender Strength - attacker Strength) × SM
    - Relationship Effect: -2
- Falling from tree
    - Node: Garden/Woods
    - Probability: 0.0005
    - Need effects:
        - Health: -10
        - Energy: -5
- Hit by car
    - Node: Street
    - Probability: 0.005
    - Need Effects:
        - Health: -60
- Infection
    - Node: Garden/Woods
    - Probability: 0.0005
    - Need Effects:
        - Health: -20
- Dog attack
    - Node: Garden/Woods
    - Probability: 0.001
    - Need effects:
        - Health: -30
        - Energy: -10

## Relationships
-10 to 10