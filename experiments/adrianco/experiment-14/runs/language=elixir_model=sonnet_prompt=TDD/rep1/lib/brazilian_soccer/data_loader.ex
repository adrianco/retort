defmodule BrazilianSoccer.DataLoader do
  @moduledoc "Parses CSV rows from the Brazilian soccer datasets."

  def normalize_team_name(name) do
    name = String.trim(name)

    # Remove " - STATE" suffix (e.g. "América - MG")
    trimmed =
      Regex.replace(~r/ - ([A-Z]{2})$/, name, "")
      |> String.trim()

    if trimmed != name do
      trimmed
    else
      # Remove "-STATE" suffix (e.g. "Palmeiras-SP")
      Regex.replace(~r/-([A-Z]{2})$/, name, "")
      |> String.trim()
    end
  end

  def parse_brasileirao_row(row) do
    case row do
      [datetime, home_raw, _home_state, away_raw, _away_state, home_goal, away_goal, season, round | _] ->
        %{
          datetime: parse_datetime(datetime),
          home_team: normalize_team_name(home_raw),
          away_team: normalize_team_name(away_raw),
          home_goal: parse_int(home_goal),
          away_goal: parse_int(away_goal),
          season: parse_int(season),
          round: parse_int(round),
          competition: "Brasileirão",
          stage: nil
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  def parse_cup_row(row) do
    case row do
      [round, datetime, home_raw, away_raw, home_goal, away_goal, season | _] ->
        %{
          datetime: parse_datetime(datetime),
          home_team: normalize_team_name(home_raw),
          away_team: normalize_team_name(away_raw),
          home_goal: parse_int(home_goal),
          away_goal: parse_int(away_goal),
          season: parse_int(season),
          round: round,
          competition: "Copa do Brasil",
          stage: round
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  def parse_libertadores_row(row) do
    case row do
      [datetime, home_raw, away_raw, home_goal, away_goal, season, stage | _] ->
        %{
          datetime: parse_datetime(datetime),
          home_team: normalize_team_name(home_raw),
          away_team: normalize_team_name(away_raw),
          home_goal: parse_int(home_goal),
          away_goal: parse_int(away_goal),
          season: parse_int(season),
          round: nil,
          competition: "Copa Libertadores",
          stage: stage
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  def parse_historico_row(row) do
    case row do
      [_id, date, ano, rodada, home_raw, away_raw, home_goal, away_goal | _] ->
        %{
          datetime: parse_br_date(date),
          home_team: normalize_team_name(home_raw),
          away_team: normalize_team_name(away_raw),
          home_goal: parse_int(home_goal),
          away_goal: parse_int(away_goal),
          season: parse_int(ano),
          round: parse_int(rodada),
          competition: "Brasileirão",
          stage: nil
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  def parse_br_football_row(row) do
    case row do
      [tournament, home_raw, home_goal, away_goal, away_raw | rest] ->
        date = Enum.at(rest, 7)

        %{
          datetime: parse_datetime(date || ""),
          home_team: normalize_team_name(home_raw),
          away_team: normalize_team_name(away_raw),
          home_goal: parse_float_as_int(home_goal),
          away_goal: parse_float_as_int(away_goal),
          season: extract_year(date || ""),
          round: nil,
          competition: tournament,
          stage: nil
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  def parse_player_row(row) do
    case row do
      [_idx, id, name, age, _photo, nationality, _flag, overall, potential,
       club | rest] ->
        [_club_logo, _value, _wage, _special, _preferred_foot, _int_rep, _weak_foot,
         _skill_moves, _work_rate, _body_type, _real_face, position, jersey | _] = rest

        %{
          id: parse_int(id),
          name: name,
          age: parse_int(age),
          nationality: nationality,
          overall: parse_int(overall),
          potential: parse_int(potential),
          club: club,
          position: String.trim(position),
          jersey_number: parse_int(jersey)
        }

      _ ->
        nil
    end
  rescue
    _ -> nil
  end

  # Date/time parsers

  defp parse_datetime(str) do
    str = String.trim(str)

    cond do
      str =~ ~r/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/ ->
        NaiveDateTime.from_iso8601!(str <> "Z") |> NaiveDateTime.to_date() |> Date.to_iso8601()

      str =~ ~r/^\d{4}-\d{2}-\d{2}$/ ->
        str

      true ->
        str
    end
  rescue
    _ -> str
  end

  defp parse_br_date(str) do
    case String.split(str, "/") do
      [day, month, year] ->
        "#{year}-#{String.pad_leading(month, 2, "0")}-#{String.pad_leading(day, 2, "0")}"

      _ ->
        str
    end
  end

  defp extract_year(str) do
    case Regex.run(~r/(\d{4})/, str) do
      [_, year] -> parse_int(year)
      _ -> nil
    end
  end

  defp parse_int(val) when is_integer(val), do: val

  defp parse_int(val) when is_binary(val) do
    val |> String.trim() |> Integer.parse() |> elem(0)
  rescue
    _ -> nil
  end

  defp parse_int(_), do: nil

  defp parse_float_as_int(val) when is_binary(val) do
    val
    |> String.trim()
    |> Float.parse()
    |> case do
      {f, _} -> round(f)
      :error -> nil
    end
  end

  defp parse_float_as_int(val), do: parse_int(val)
end
