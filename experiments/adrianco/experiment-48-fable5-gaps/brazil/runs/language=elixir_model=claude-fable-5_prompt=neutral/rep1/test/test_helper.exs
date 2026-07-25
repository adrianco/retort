# Load the datasets once for the whole suite (shared via :persistent_term).
BrazilianSoccerMcp.DataStore.ensure_loaded!()
ExUnit.start()
