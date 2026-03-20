# 10. Keep `finished_at` field to record when simulation failed
 
Date: 2026-03-20

## Status
Accepted

## Context
When implementing the pause and cancel endpoints it became apparent that using `finished_at` to persist the time of the state transformation, would be unclean architecture this field should really only be updated on mark_completed(). A new field `stopped_at` was therefore created. Obviously a failed simulation therefore should be updated by changing the `stopped_at` field as well to keep everything clean.

## Decision Drivers
Updating the `stopped_at` field instead of the `finished_at` field when a simulation fails, would mean a breaking change (even if only minor) for the API as we have been exposing the `finished_at` field alongside the `state`on the SimulationList Endpoint and therefore a client might be relying on the implicit connection between a simulation having a `FAILED` state and a `finished_at` field set

## Considered Options
- implement the breaking change and release a new API version
- defer the implementation to a later planned date, when technical debt for a new API version release seems more reasonable (chosen)

## Decision
The inconsistency of setting `finished_at` instead of `stopped_at` when a simulation fails seems rather minor, even though not ideal and can be deferred to be fixed at a later time. The upside of not releasing a breaking change shortly after the first versioned API release seems much stronger.

## Consequences
- lesser readability both of the code and the API, seeing the field `finished_at` set might cause some confusion
- no breaking change of the API
- when a new API is released eventually, this change needs to be incorporated - I added a TODO comment right above the .mark_failed() method, so hopefully this will be caught
