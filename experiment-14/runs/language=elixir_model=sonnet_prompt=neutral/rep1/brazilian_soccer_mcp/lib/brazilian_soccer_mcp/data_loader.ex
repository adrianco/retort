defmodule BrazilianSoccerMcp.DataLoader do
  @moduledoc """
  Loads CSV data files into in-memory structures.
  """

  NimbleCSV.define(CSVParser, separator: ",", escape: "\"")

  @data_dir Path.join([File.cwd!(), "..", "data", "kaggle"])

  def data_dir, do: @data_dir

  def load_all do
    %{
      brasileirao: load_brasileirao(),
      copa_brasil: load_copa_brasil(),
      libertadores: load_libertadores(),
      extended: load_extended(),
      historical: load_historical(),
      players: load_players()
    }
  end

  def load_brasileirao do
    path = Path.join(@data_dir, "Brasileirao_Matches.csv")
    parse_csv(path, &parse_brasileirao_row/1)
  end

  def load_copa_brasil do
    path = Path.join(@data_dir, "Brazilian_Cup_Matches.csv")
    parse_csv(path, &parse_copa_brasil_row/1)
  end

  def load_libertadores do
    path = Path.join(@data_dir, "Libertadores_Matches.csv")
    parse_csv(path, &parse_libertadores_row/1)
  end

  def load_extended do
    path = Path.join(@data_dir, "BR-Football-Dataset.csv")
    parse_csv(path, &parse_extended_row/1)
  end

  def load_historical do
    path = Path.join(@data_dir, "novo_campeonato_brasileiro.csv")
    parse_csv(path, &parse_historical_row/1)
  end

  def load_players do
    path = Path.join(@data_dir, "fifa_data.csv")
    parse_csv(path, &parse_player_row/1)
  end

  defp parse_csv(path, row_parser) do
    path
    |> File.stream!(read_ahead: 100_000)
    |> CSVParser.parse_stream(skip_headers: true)
    |> Stream.map(row_parser)
    |> Stream.reject(&is_nil/1)
    |> Enum.to_list()
  rescue
    e ->
      IO.warn("Failed to load #{path}: #{Exception.message(e)}")
      []
  end

  defp parse_brasileirao_row([datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round | _]) do
    %{
      competition: :brasileirao,
      datetime: parse_datetime(datetime),
      home_team: home_team,
      away_team: away_team,
      home_team_state: home_team_state,
      away_team_state: away_team_state,
      home_goal: parse_int(home_goal),
      away_goal: parse_int(away_goal),
      season: parse_int(season),
      round: round,
      stage: nil
    }
  end
  defp parse_brasileirao_row(_), do: nil

  defp parse_copa_brasil_row([round, datetime, home_team, away_team, home_goal, away_goal, season | _]) do
    %{
      competition: :copa_brasil,
      datetime: parse_datetime(datetime),
      home_team: home_team,
      away_team: away_team,
      home_team_state: nil,
      away_team_state: nil,
      home_goal: parse_int(home_goal),
      away_goal: parse_int(away_goal),
      season: parse_int(season),
      round: round,
      stage: round
    }
  end
  defp parse_copa_brasil_row(_), do: nil

  defp parse_libertadores_row([datetime, home_team, away_team, home_goal, away_goal, season, stage | _]) do
    %{
      competition: :libertadores,
      datetime: parse_datetime(datetime),
      home_team: home_team,
      away_team: away_team,
      home_team_state: nil,
      away_team_state: nil,
      home_goal: parse_int(home_goal),
      away_goal: parse_int(away_goal),
      season: parse_int(season),
      round: nil,
      stage: stage
    }
  end
  defp parse_libertadores_row(_), do: nil

  defp parse_extended_row([tournament, home, home_goal, away_goal, away, home_corner, away_corner, home_attack, away_attack, home_shots, away_shots, _time, date | _]) do
    %{
      competition: :extended,
      tournament: tournament,
      datetime: parse_datetime(date),
      home_team: home,
      away_team: away,
      home_team_state: nil,
      away_team_state: nil,
      home_goal: parse_float_to_int(home_goal),
      away_goal: parse_float_to_int(away_goal),
      home_corner: parse_float_to_int(home_corner),
      away_corner: parse_float_to_int(away_corner),
      home_attack: parse_float_to_int(home_attack),
      away_attack: parse_float_to_int(away_attack),
      home_shots: parse_float_to_int(home_shots),
      away_shots: parse_float_to_int(away_shots),
      season: extract_year(date),
      round: nil,
      stage: nil
    }
  end
  defp parse_extended_row(_), do: nil

  defp parse_historical_row([id, date, year, round, home_team, away_team, home_goal, away_goal, home_state, away_state, winner, arena | _]) do
    %{
      competition: :historical,
      id: id,
      datetime: parse_datetime(date),
      home_team: home_team,
      away_team: away_team,
      home_team_state: home_state,
      away_team_state: away_state,
      home_goal: parse_int(home_goal),
      away_goal: parse_int(away_goal),
      season: parse_int(year),
      round: round,
      winner: winner,
      arena: arena,
      stage: nil
    }
  end
  defp parse_historical_row(_), do: nil

  defp parse_player_row([_idx, id, name, age, _photo, nationality, _flag, overall, potential,
                         club, _logo, value, wage, _special, preferred_foot, intl_rep,
                         weak_foot, skill_moves, work_rate, _body_type, _real_face,
                         position, jersey_number | _rest]) do
    %{
      id: parse_int(id),
      name: name,
      age: parse_int(age),
      nationality: nationality,
      overall: parse_int(overall),
      potential: parse_int(potential),
      club: club,
      value: value,
      wage: wage,
      preferred_foot: preferred_foot,
      intl_reputation: parse_int(intl_rep),
      weak_foot: parse_int(weak_foot),
      skill_moves: parse_int(skill_moves),
      work_rate: work_rate,
      position: position,
      jersey_number: jersey_number
    }
  end
  defp parse_player_row(_), do: nil

  # Date/time parsing

  defp parse_datetime(""), do: nil
  defp parse_datetime(nil), do: nil

  defp parse_datetime(str) do
    str = String.trim(str)
    cond do
      # ISO with time: "2012-05-19 18:30:00"
      Regex.match?(~r/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/, str) ->
        String.slice(str, 0, 10)

      # ISO date: "2023-09-24"
      Regex.match?(~r/^\d{4}-\d{2}-\d{2}$/, str) ->
        str

      # Brazilian: "29/03/2003"
      Regex.match?(~r/^\d{2}\/\d{2}\/\d{4}$/, str) ->
        [d, m, y] = String.split(str, "/")
        "#{y}-#{m}-#{d}"

      true ->
        str
    end
  end

  defp extract_year(date_str) do
    cond do
      Regex.match?(~r/^(\d{4})-/, date_str) ->
        date_str |> String.slice(0, 4) |> parse_int()

      Regex.match?(~r/^\d{2}\/\d{2}\/(\d{4})$/, date_str) ->
        date_str |> String.slice(-4, 4) |> parse_int()

      true ->
        nil
    end
  end

  defp parse_int(""), do: nil
  defp parse_int(nil), do: nil
  defp parse_int(str) when is_binary(str) do
    case Integer.parse(String.trim(str)) do
      {n, _} -> n
      :error -> nil
    end
  end
  defp parse_int(n) when is_integer(n), do: n

  defp parse_float_to_int(""), do: nil
  defp parse_float_to_int(nil), do: nil
  defp parse_float_to_int(str) when is_binary(str) do
    case Float.parse(String.trim(str)) do
      {f, _} -> round(f)
      :error -> parse_int(str)
    end
  end
end
