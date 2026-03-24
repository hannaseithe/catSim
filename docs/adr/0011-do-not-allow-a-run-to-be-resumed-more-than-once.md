# 11. Do not allow a run to be resumed more than once

Date: 2026-03-23

## Status
Accepted

## Context
Currently on the resume endpoint we allow a simulation run to be queued more than once, while the simulation is already being queued. 

## Decision Drivers
Since a simulation run is deterministic using the same seed parameter and the resume endpoint does not change that, a resume should only be run once.

## Considered Options
- allow multiple resumes
- allow only one resume (chosen)

## Decision
Since a simulation is deterministic (when seeded) by nature, it makes no sense to allow multiple runs of resume. Since it is not unlikely though, that a simulation can be waiting for resume in the celery queue for a while and a client might chose to trigger the endpoint again, the resume endpoint needs to be protected from multiple queuing. 

## Consequences
- a resume is only queued once
- multiple calls to the resume endpoint for the same run, will return a 409 response, analogue to the start point handling of idempotency
