# Interfaces

## MCP tools (stdio JSON-RPC 2.0)

Exactly 12 tools listed by `tools/list`, in reference order (`mcp/tools_schema.go`), dispatched in `tools/tools.go:Execute`:

| Tool | Required args | Purpose |
|------|---------------|---------|
| search_entities | query | Name/content search, optional type filter + limit |
| get_entity_details | entity_id | Entity + incoming/outgoing relationships |
| create_entity | entity_type, name, content | Mint a new versioned entity |
| update_entity | entity_id, changes | New immutable version with merged content |
| create_relationship | from_entity_id, to_entity_id, relationship_type | Directed edge |
| get_devices_in_room | room_id | Devices `located_in` a room |
| find_device_controls | device_id | Capabilities/services/controlled devices |
| get_room_connections | room_id | Rooms adjacent via door/window connectors |
| find_path | from_entity_id, to_entity_id | Undirected BFS path over edges |
| find_similar_entities | entity_id | Same-type/content similarity |
| get_procedures_for_device | device_id | Procedures/manuals for a device |
| get_automations_in_room | room_id | Automations/schedules for a room |

JSON-RPC methods handled: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`.

## Sync HTTP client (outbound)

`POST {FUNKYGIBBON_URL}/api/v1/sync/` with `Authorization: Bearer <token>` and `Content-Type: application/json`. Body is a `SyncRequest`; response is a `SyncResponse`.

## Data schema

**Entity**: id, version, entity_type, name, content (arbitrary JSON), source_type, user_id, parent_versions, updated_at (derived from version). **Relationship**: id, from_entity_id/_version, to_entity_id/_version, relationship_type, properties. Persisted as one JSON document (`wombat-go.db.json`): `{entities, relationships, watermark}`.

## Configuration (env)

`FUNKYGIBBON_URL`, `FUNKYGIBBON_AUTH_TOKEN`, `FUNKYGIBBON_DEVICE_ID`, `FUNKYGIBBON_USER_ID`, `SYNC_INTERVAL_SECONDS`, `WOMBAT_DB`, `WOMBAT_SEED`.
