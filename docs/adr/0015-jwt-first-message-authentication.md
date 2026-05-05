# 15. JWT First message authentication

Date: 2026-05-05

## Status
Accepted

## Context
It is necessary to only allow authenticated and only the run's owner or staff access to specific websocket connections for event emission. Since we use stateless JWT for access to the HTTP part of the application, JWT should be used as well.

## Decision Drivers
The already implemented JWT authentication is stateless and should therefore also be stateless for the websocket (no cookies), furthermore we do not want to expose the token as a URL querystring (which is necessary if the client is a browser). 

## Considered Options
- Authenticate token on connect through querystring and CustomMiddleware (need to expose token through querystring)
- Authenticate token on connect through cookie (would need a refactor of the whole stateless jwt authentication approach)
- Authenticate token on connect through subprotocol (seems like a rather unclean solution)
- Authenticate token on first message through message body and set timeout on connect call to disconnect if not authenticated (CHOSEN)

## Decision
The client sends the handshake GET without any authentication data, receives a connection, and then needs to immediately send a first message with the token in the messages payload to be authenticated, otherwise the connection will be closed after 5 seconds. Once the connection is authenticated the consumer will begin to emit events for the requested simulation run.

## Consequences
- the token credentials are hidden from browser history, server logs
- the initial unauthenticated connection will stay open for 5 seconds (configurable through settings.py)
