# 8. Checkpoint Resume Logic

Date: 2026-03-20

## Status
Accepted

## Context
A user should be able to resume a simulation that was canceled or paused. As the running a simulation is handled asynchronously and separate from the persistence layer. The coordination of the workflow and the assurance of data integrity needs throrough architectural design that will last

## Decision Drivers
In order to resume we need a way to persist the state of the simulation at certain tick-interval based checkpoints, and a way to transfer simulation state to persistene layer and back for resumption. 

## Considered Options
- do not implement the checkpoint structure and keep things as they are
- implement a tick interval based checkpoint logic. Keep only the latest state saved in DB. Inside the simulation engine define the serialization and deserialization logic for state. Define a single time resume logic(chosen)
- keep all saved checkpoints in a separate table, which then would allow starting resuming from earlier points in time


## Decision
It was decided to implement the checkpoint and resume logic as part of the coordination layer between Django and the simulation engine. On each checkpoint, a serialized simulation state will be pulled from the simulation and persisted to django. During resume (triggered by an endpoint), the saved checkpoint is pulled from the DB handed over to the simulation to be deserialized again. The contract between SimulationState(SimulationEngine) & Serialized JSON Structure (Django) is owned and defined by the simulation engine, that both ensures validation and transformation. Django only saves the serialized state as an opaque JSONField, on which it performs no validation. 

## Consequences
- ensures decoupling of simulation and persistence/API layer
- validation of SimulationState is only ensured at the coordination layer, if data corrupts inside the database, it will only be caught during de-serialization
- Keeping the coordination logic all inside tasks.py holds the risk of incrementally moving towards a "fat" controller
