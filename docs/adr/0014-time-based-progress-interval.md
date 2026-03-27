# 14. Time based ProgressEvent interval 

Date: 2026-03-27

## Status
Accepted

## Context
We need to log ProgressEvent while the simulation loop runs and we have access to the tick value of the simulation

## Decision Drivers
The duration of a tick itself, can vary greatly between simulations. Therefore basing Progress reports on ticks alone is very unreliable. At the same time, there is no point in reporting more often than a tick, because progress is measure by tick

## Considered Options
- emit a ProgressEvent every tick
- set a minimum progress report duration, after only which a progress event is emited during a tick step (chosen)
- user background threat to pull state from simulation and emit every duration interval

## Decision
We set a `SIMULATION_PROGRESS_INTERVAL_DURATION` in settings, which represents the time interval in seconds after which we release the next ProgressEvent from within the simulation loop 

## Consequences
- if a tick takes longer than the progress_interval_duration the event will be emitted as often as a tick is finished.
- on the other hand we can rely on that it will not be emitted faster (or more often) if the tick takes less time than the progress_interval_duration

