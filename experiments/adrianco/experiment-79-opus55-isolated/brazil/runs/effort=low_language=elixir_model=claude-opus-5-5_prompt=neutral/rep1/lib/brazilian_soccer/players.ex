defmodule BrazilianSoccer.Players do
  @moduledoc "Queries over the FIFA player dataset."

  alias BrazilianSoccer.{Store, Teams, Text}

  @groups %{
    "goalkeeper" => ~w(GK),
    "defender" => ~w(CB LCB RCB LB RB LWB RWB),
    "midfielder" => ~w(CM LCM RCM CDM LDM RDM CAM LAM RAM LM RM),
    "forward" => ~w(ST LS RS CF LF RF LW RW)
  }

  @doc """
  Searches players. Options (all optional): `:name`, `:nationality`, `:club`,
  `:position` (a FIFA code such as "ST" or a group such as "forwards"),
  `:min_overall`, `:max_age`, `:sort_by` ("overall" | "potential" | "age" |
  "name"). Results are sorted best-first by default.
  """
  def search(opts \\ %{}) do
    name = fold_opt(opts[:name])
    nat = fold_opt(opts[:nationality]) |> nationality_alias()
    club = fold_opt(opts[:club])
    club_key = club && Teams.resolve(opts[:club]).key
    positions = positions(opts[:position])
    min = Text.parse_int(opts[:min_overall])
    max_age = Text.parse_int(opts[:max_age])

    Store.players()
    |> Enum.filter(fn p ->
      (name == nil or name_match?(p.name_fold, name)) and
        (nat == nil or p.nationality_fold == nat) and
        (club == nil or club_match?(p, club, club_key)) and
        (positions == nil or p.position in positions) and
        (min == nil or (p.overall || 0) >= min) and
        (max_age == nil or (p.age || 999) <= max_age)
    end)
    |> sort(opts[:sort_by])
  end

  @doc "Counts and average rating per club for players matching the filters."
  def by_club(opts \\ %{}) do
    brazilian_only = opts[:brazilian_clubs_only]

    opts
    |> search()
    |> Enum.filter(&(&1.club != nil))
    |> Enum.filter(&(not brazilian_only or Teams.brazilian_club?(&1.club_key)))
    |> Enum.group_by(& &1.club)
    |> Enum.map(fn {club, ps} ->
      rated = Enum.filter(ps, & &1.overall)

      %{
        club: club,
        players: length(ps),
        avg_overall:
          Float.round(Enum.sum(Enum.map(rated, & &1.overall)) / max(length(rated), 1), 1),
        best: List.first(ps)
      }
    end)
    |> Enum.sort_by(&{-&1.players, -&1.avg_overall, &1.club})
  end

  defp fold_opt(nil), do: nil

  defp fold_opt(s) do
    case Text.fold(to_string(s)) do
      "" -> nil
      f -> f
    end
  end

  defp nationality_alias(n) when n in ["brazilian", "brasil", "brasileiro", "brasileiros"],
    do: "brazil"

  defp nationality_alias(n), do: n

  # Every word of the query must appear in the name ("gabriel barbosa").
  defp name_match?(name, query) do
    String.contains?(name, query) or
      Enum.all?(String.split(query, " ", trim: true), &String.contains?(name, &1))
  end

  defp club_match?(%{club: nil}, _, _), do: false

  defp club_match?(p, club, club_key),
    do: p.club_key == club_key or String.contains?(p.club_fold, club)

  defp positions(nil), do: nil

  defp positions(pos) do
    f = Text.fold(pos)

    cond do
      f == "" -> nil
      f =~ ~r/^(forward|attack|striker)/ -> @groups["forward"]
      f =~ ~r/^mid/ -> @groups["midfielder"]
      f =~ ~r/^(defen|back)/ -> @groups["defender"]
      f =~ ~r/^(goal|keeper)/ -> @groups["goalkeeper"]
      true -> [String.upcase(f)]
    end
  end

  defp sort(ps, "name"), do: Enum.sort_by(ps, & &1.name_fold)
  defp sort(ps, "age"), do: Enum.sort_by(ps, &{&1.age || 999, -(&1.overall || 0)})
  defp sort(ps, "potential"), do: Enum.sort_by(ps, &{-(&1.potential || 0), -(&1.overall || 0)})

  defp sort(ps, _),
    do: Enum.sort_by(ps, &{-(&1.overall || 0), -(&1.potential || 0), &1.name_fold})
end
