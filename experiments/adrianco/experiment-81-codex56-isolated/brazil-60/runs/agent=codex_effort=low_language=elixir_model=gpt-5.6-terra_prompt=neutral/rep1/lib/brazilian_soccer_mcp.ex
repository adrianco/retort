defmodule BrazilianSoccerMcp do
  @moduledoc "Knowledge-graph-like query interface over the bundled Brazilian football CSV data."

  alias BrazilianSoccerMcp.{Data, Query}

  def load(data_dir \\ default_data_dir()), do: Data.load(data_dir)
  def default_data_dir, do: Path.expand("data/kaggle", File.cwd!())
  def matches(filters \\ %{}), do: Query.matches(Data.all_matches(), filters)
  def players(filters \\ %{}), do: Query.players(Data.players(), filters)
  def team_stats(team, filters \\ %{}), do: Query.team_stats(Data.all_matches(), team, filters)

  def head_to_head(first, second, filters \\ %{}),
    do: Query.head_to_head(Data.all_matches(), first, second, filters)

  def standings(season, competition \\ "Brasileirao"),
    do: Query.standings(Data.all_matches(), season, competition)

  def aggregate(filters \\ %{}), do: Query.aggregate(Data.all_matches(), filters)
end
