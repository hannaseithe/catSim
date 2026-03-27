# 13. Store events in the DB

Date: 2026-03-27

## Status
Accepted

## Context
We want to provide clients with a comprehensive information (or stream in the future) of relevant events of their simulation. 

## Decision Drivers
Events should not only be a debugging tool for the admin, but a reliable information source for clients. If events are only saved in log files, this will be difficult to filter (per client or event_type) or use for analytics.

## Considered Options
- log relevant events through the logger to log files
- save events to the DB with consistent event_type validation (chosen)

## Decision
We will log events as SimulationEvents to the Database, allowing for different types of events (ProgressEvent, StateTransitionEvent, QueueEvent). 

## Consequences
- each event creation involves a row write to the DB, which might impact performance
- events have a clear structure, which can be relied upon for filtering and aggregation

