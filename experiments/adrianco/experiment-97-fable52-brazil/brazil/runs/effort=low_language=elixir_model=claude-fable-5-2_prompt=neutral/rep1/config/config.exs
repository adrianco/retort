import Config

# stdout is reserved for the MCP JSON-RPC stream; send all logging to stderr.
config :logger, :default_handler, config: [type: :standard_error]
