# 6. Version the API Using URL-Based Versioning

Date: 2026-02-14

## Status
Accepted

## Context
As the API evolves, breaking changes may be introduced.  
To support backward compatibility and allow clients to upgrade gradually, a versioning strategy is required.

## Decision Drivers
- Provide backward compatibility for existing clients  
- Enable evolution of the API without breaking current users  
- Clear and discoverable versioning scheme

## Considered Options
- Header-based versioning  
- URL-based versioning (chosen)  
- No versioning

## Decision
The API will use URL-based versioning (e.g., `/api/v1/...`).  
The unversioned API will be deprecated, and clients are expected to migrate to the versioned endpoints.

## Consequences
- Clear versioning visible in the URL  
- Easier routing and documentation  
- Deprecation of unversioned endpoints requires communicating with clients