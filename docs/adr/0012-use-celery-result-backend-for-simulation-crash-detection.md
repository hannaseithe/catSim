# 12. Use Celery Result Backend to detect Crashed Simulation Runs

Date: 2026-03-26

## Status
Accepted

## Context
We need to be able to detect whether a celery process running a specific simulation has crashed in order to restart on celery restart

## Decision Drivers
- checking a celery processes state directly gives clear feedback on what happened to the process
- a heartbeat solution would be more unreliable as a simulations tick's duration can vary greatly depending on the parameters

## Considered Options
- using the CELERY_RESULT_BACKEND to check a specific simulation run's celery state (chosen)
- using a heartbeat field on the model to assure that a run is still actually running

## Decision
The CELERY_RESULT_BACKEND will be set to redis and used for detection of celery's process state of a specific simulation run to determine whether a process has crashed mid-simulation or not

## Consequences
- performance might be impacted as Celery now has to write to the result_backend
- we have a reliable way to understand a celery processes state
