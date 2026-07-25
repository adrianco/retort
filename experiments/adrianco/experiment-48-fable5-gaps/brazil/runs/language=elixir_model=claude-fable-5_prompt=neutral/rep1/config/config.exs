import Config

# The MCP stdio transport owns stdout: only JSON-RPC messages may be written
# there. Send all log output to stderr.
config :logger, :default_handler, config: [type: :standard_error]
