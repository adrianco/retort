defmodule SoccerMcp.Store do
  @moduledoc """
  The loaded dataset: every match from the six CSV files in one list, and
  every player from the FIFA database.

  The Brasileirão files overlap (2012-2019 appear in more than one), and the
  extended statistics file repeats some Serie A and Copa do Brasil matches.
  `load/1` keeps the first of any rows that describe the same match (same
  competition, season and ordered teams, dates within three days), in the
  order the files are listed in `@match_files`, so every real match is
  counted once.
  """

  alias SoccerMcp.{CSV, Match, Parse, Player, Team}

  defstruct matches: [], players: [], sources: []

  @type t :: %__MODULE__{
          matches: [Match.t()],
          players: [Player.t()],
          sources: [{String.t(), non_neg_integer()}]
        }

  # Order matters: earlier files win when the same match appears twice.
  @match_files [
    {"Brasileirao_Matches.csv", :brasileirao_matches},
    {"novo_campeonato_brasileiro.csv", :historical_brasileirao},
    {"Brazilian_Cup_Matches.csv", :cup_matches},
    {"Libertadores_Matches.csv", :libertadores_matches},
    {"BR-Football-Dataset.csv", :extended_matches}
  ]

  @player_file "fifa_data.csv"

  @doc """
  Loads all datasets from `dir`. Writes a one-line summary per file to
  stderr, so stdout stays clean for the MCP protocol.
  """
  @spec load(Path.t()) :: t()
  def load(dir) do
    {matches, sources} =
      Enum.reduce(@match_files, {[], []}, fn {file, kind}, {acc, sources} ->
        rows = CSV.parse_file(Path.join(dir, file))
        parsed = rows |> Enum.map(&parse_match(kind, &1, file)) |> Enum.reject(&is_nil/1)
        {[parsed | acc], [{file, length(parsed)} | sources]}
      end)

    all_matches =
      matches
      |> Enum.reverse()
      |> Enum.concat()
      |> dedupe()
      |> mark_cup_finals()
      |> Enum.sort_by(&{&1.date, &1.competition, &1.home})

    players =
      dir
      |> Path.join(@player_file)
      |> CSV.parse_file()
      |> Enum.map(&Player.from_row/1)

    sources = Enum.reverse(sources) ++ [{@player_file, length(players)}]

    for {file, count} <- sources do
      IO.puts(:stderr, "loaded #{count} records from #{file}")
    end

    %__MODULE__{matches: all_matches, players: players, sources: sources}
  end

  @doc """
  Parses one row from a match file into a `Match`, or `nil` when the row has
  no date, no scores (unplayed), or an unknown competition.
  """
  @spec parse_match(atom(), map(), String.t()) :: Match.t() | nil
  def parse_match(:brasileirao_matches, row, file) do
    build(row["home_team"], row["away_team"], row["datetime"], row["home_goal"], row["away_goal"],
      competition: "Brasileirão Série A",
      season: row["season"],
      stage: row["round"] && "Round #{row["round"]}",
      source: file
    )
  end

  def parse_match(:historical_brasileirao, row, file) do
    build(
      row["Equipe_mandante"],
      row["Equipe_visitante"],
      row["Data"],
      row["Gols_mandante"],
      row["Gols_visitante"],
      competition: "Brasileirão Série A",
      season: row["Ano"],
      stage: row["Rodada"] && "Round #{row["Rodada"]}",
      home_state: state_column(row["Mandante_UF"]),
      away_state: state_column(row["Visitante_UF"]),
      source: file
    )
  end

  def parse_match(:cup_matches, row, file) do
    build(row["home_team"], row["away_team"], row["datetime"], row["home_goal"], row["away_goal"],
      competition: "Copa do Brasil",
      season: row["season"],
      stage: cup_round_label(row["round"]),
      source: file
    )
  end

  def parse_match(:libertadores_matches, row, file) do
    build(row["home_team"], row["away_team"], row["datetime"], row["home_goal"], row["away_goal"],
      competition: "Copa Libertadores",
      season: row["season"],
      stage: row["stage"],
      source: file
    )
  end

  def parse_match(:extended_matches, row, file) do
    build(row["home"], row["away"], row["date"], row["home_goal"], row["away_goal"],
      competition: Match.canonical_competition(row["tournament"]),
      season: nil,
      stage: nil,
      source: file
    )
  end

  defp state_column(nil), do: nil

  defp state_column(text) do
    case String.trim(text) |> String.downcase() do
      "" -> nil
      uf -> uf
    end
  end

  defp cup_round_label(nil), do: nil

  defp cup_round_label(round) do
    case Integer.parse(String.trim(round)) do
      {n, ""} -> "Round #{n}"
      _ -> String.trim(round)
    end
  end

  # The Copa do Brasil final is the last numbered round of a season when that
  # round is two legs (at most two matches). Seasons whose last round is a
  # larger group-style round are left alone.
  defp mark_cup_finals(matches) do
    numbered =
      Enum.filter(matches, &(&1.competition == "Copa do Brasil" and round_number(&1.stage)))

    sizes = Enum.frequencies_by(numbered, &{&1.season, round_number(&1.stage)})

    final_rounds =
      numbered
      |> Enum.group_by(& &1.season, &round_number(&1.stage))
      |> Enum.flat_map(fn {season, rounds} ->
        last = Enum.max(rounds)
        if Map.get(sizes, {season, last}, 0) <= 2, do: [{season, last}], else: []
      end)
      |> MapSet.new()

    Enum.map(matches, fn m ->
      round = round_number(m.stage)

      if m.competition == "Copa do Brasil" and round != nil and
           MapSet.member?(final_rounds, {m.season, round}) do
        %{m | stage: "final"}
      else
        m
      end
    end)
  end

  defp round_number("Round " <> n) do
    case Integer.parse(n) do
      {number, ""} -> number
      _ -> nil
    end
  end

  defp round_number(_stage), do: nil

  defp build(home, away, date_text, home_goals, away_goals, opts) do
    date = Parse.date(date_text)
    hg = Parse.int(home_goals)
    ag = Parse.int(away_goals)
    competition = Keyword.fetch!(opts, :competition)

    if date && hg && ag && competition && home not in [nil, ""] && away not in [nil, ""] do
      season = Parse.int(opts[:season]) || date.year

      Match.new(
        home,
        away,
        date,
        hg,
        ag,
        competition,
        season,
        Keyword.take(opts, [:stage, :source, :home_state, :away_state])
      )
    end
  end

  # Two rows describe the same match when they share competition, season and
  # ordered home/away pair, their dates are within @duplicate_window_days, and
  # their states do not contradict each other (Atlético-MG and Atlético-GO
  # share a key but are different clubs). The first row seen wins.
  @duplicate_window_days 3

  defp dedupe(matches) do
    {kept, _seen} =
      Enum.flat_map_reduce(matches, %{}, fn match, seen ->
        key = {match.competition, match.season, match.home_key, match.away_key}
        earlier = Map.get(seen, key, [])

        if Enum.any?(earlier, &same_match?(&1, match)) do
          {[], seen}
        else
          {[match], Map.update(seen, key, [match], &[match | &1])}
        end
      end)

    kept
  end

  defp same_match?(a, b) do
    abs(Date.diff(a.date, b.date)) <= @duplicate_window_days and
      Team.compatible_states?(a.home_state, b.home_state) and
      Team.compatible_states?(a.away_state, b.away_state)
  end

  @doc "Normalized team keys present in the match data, sorted."
  @spec team_keys(t()) :: [String.t()]
  def team_keys(%__MODULE__{matches: matches}) do
    matches
    |> Enum.flat_map(&[&1.home_key, &1.away_key])
    |> Enum.uniq()
    |> Enum.reject(&(&1 == ""))
    |> Enum.sort()
  end
end
