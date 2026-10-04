import Config

# stdout is reserved for the MCP JSON-RPC stream, so logs go to stderr.
config :logger, :default_handler, config: [type: :standard_error]
config :logger, level: :warning
