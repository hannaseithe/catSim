# 7. Use JWT Authentication for API Access

Date: 2026-01-19

## Status
Accepted

## Context
The API requires secure authentication to protect simulation data and ensure only authorized clients can start simulations or access results.

## Decision Drivers
- Provide stateless, secure authentication  
- Support modern API clients, including web and CLI tools  
- Minimize server-side session management complexity

## Considered Options
- Session-based authentication  
- JSON Web Tokens (JWT) (chosen)

## Decision
JWT authentication will be used for all API access.  
Clients must include a valid JWT in the `Authorization` header to access endpoints.

## Consequences
- Stateless authentication, suitable for distributed deployments  
- Simplifies API client implementation  
- Requires careful handling of token expiration and revocation