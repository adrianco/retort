import Config

# Tests inject their own fixture data, so don't load CSVs at boot.
config :brasil_soccer, start_store: false
