import Config

# Where the Kaggle CSV files live, relative to the project root.
config :brasil_soccer, data_dir: "data/kaggle"

import_config "#{config_env()}.exs"
