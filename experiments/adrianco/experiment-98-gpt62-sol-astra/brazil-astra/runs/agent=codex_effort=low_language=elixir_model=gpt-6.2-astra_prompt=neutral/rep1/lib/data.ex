defmodule Soccer.Data do
  @files ~w(Brasileirao_Matches novo_campeonato_brasileiro Brazilian_Cup_Matches Libertadores_Matches BR-Football-Dataset)
  @states ~w(ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to)
  @aliases %{
    "sport club corinthians paulista" => "corinthians",
    "sao paulo fc" => "sao paulo",
    "clube de regatas do flamengo" => "flamengo",
    "sociedade esportiva palmeiras" => "palmeiras",
    "vasco" => "vasco da gama",
    "atletico mineiro" => "atletico-mg",
    "atletico goianiense" => "atletico-go",
    "atletico paranaense" => "atletico-pr",
    "athletico paranaense" => "atletico-pr",
    "athletico-pr" => "atletico-pr",
    "athletico" => "atletico-pr",
    "sport recife" => "sport",
    "ec bahia" => "bahia",
    "ec juventude" => "juventude",
    "fortaleza fc" => "fortaleza",
    "santa cruz fc" => "santa cruz",
    "red bull bragantino" => "bragantino",
    "nautico capibaribe" => "nautico",
    "botafogo-rj" => "botafogo",
    "america fc (minas gerais)" => "america-mg",
    "sport club do recife" => "sport",
    "ceara sporting club" => "ceara"
  }
  def fold(s),
    do:
      s
      |> String.downcase()
      |> String.normalize(:nfd)
      |> String.replace(~r/\p{Mn}/u, "")
      |> String.trim()

  def team(s) do
    name = fold(s)

    key =
      case Regex.run(~r/^(.+?)(?:\s*-\s*|\s+)([a-z]{2})$/, name) do
        [_, base, state] when state in @states ->
          if base in ~w(atletico athletico america botafogo nacional operario ferroviario),
            do: base <> "-" <> state,
            else: base

        _ ->
          name
      end

    Map.get(@aliases, key, key)
  end

  def rows(path) do
    [head | lines] = File.read!(path) |> String.split(~r/\r?\n/, trim: true)
    keys = fields(head)
    Enum.map(lines, fn line -> Map.new(Enum.zip(keys, fields(line))) end)
  end

  defp fields(line) do
    if String.contains?(line, "\"") do
      Regex.scan(~r/(?:^|,)(?:"((?:[^"]|"")*)"|([^,]*))/, line)
      |> Enum.map(fn
        [_, quoted] -> String.replace(quoted, "\"\"", "\"")
        [_, _, plain] -> plain
      end)
    else
      :binary.split(line, ",", [:global])
    end
  end

  def date(s) do
    case String.split(s, "/") do
      [d, m, y] ->
        Enum.join([y, String.pad_leading(m, 2, "0"), String.pad_leading(d, 2, "0")], "-")

      [_] ->
        String.slice(s, 0, 10)
    end
  end

  defp number(s) do
    case Integer.parse(s || "") do
      {n, _} -> n
      :error -> nil
    end
  end

  def load(dir \\ "data/kaggle") do
    raw = for file <- @files, r <- rows(Path.join(dir, file <> ".csv")), do: match(file, r)
    # Reconcile by date first. Some sources record the next UTC calendar day.
    {_, merged} =
      Enum.reduce(raw, {%{}, %{}}, fn m, {dates, fixtures} ->
        pair = {m.competition, m.home, m.away}

        day =
          case Date.from_iso8601(m.date) do
            {:ok, date} -> Date.to_gregorian_days(date)
            _ -> -System.unique_integer([:positive]) * 10
          end

        nearby = Enum.find_value([day, day - 1, day + 1], &dates[{pair, &1}])
        key = nearby || if m.competition == "Serie A", do: {pair, m.season}, else: {pair, day}

        # Preserve distinct rounds when a source repeats a home/away pairing.
        key =
          case fixtures[key] do
            %{source: source, round: round} when source == m.source and round != m.round ->
              {pair, day}

            _ ->
              key
          end

        combined =
          Map.update(fixtures, key, m, fn old ->
            %{
              old
              | date: if(old.date == "NA", do: m.date, else: old.date),
                home_goal: old.home_goal || m.home_goal,
                away_goal: old.away_goal || m.away_goal,
                details: Map.merge(m.details, old.details)
            }
          end)

        {Map.put(dates, {pair, day}, key), combined}
      end)

    players =
      for r <- rows(Path.join(dir, "fifa_data.csv")),
          do: %{
            club: team(r["Club"]),
            name: fold(r["Name"]),
            nationality: fold(r["Nationality"]),
            rating: number(r["Overall"]),
            data: r
          }

    %{raw: raw, matches: Map.values(merged), players: Enum.sort_by(players, & &1.rating, :desc)}
  end

  defp match(file, r) do
    date = date(r["datetime"] || r["Data"] || r["date"])
    season = number(r["season"] || r["Ano"] || date)
    round = r["round"] || r["Rodada"]

    competition =
      case file do
        "Brazilian_Cup_Matches" -> "Copa do Brasil"
        "Libertadores_Matches" -> "Libertadores"
        _ -> r["tournament"] || "Serie A"
      end

    stage =
      cond do
        r["stage"] ->
          r["stage"]

        competition == "Copa do Brasil" && round &&
            ((season == 2012 && round == "6") || (season == 2016 && round == "7") || round == "8") ->
          "final"

        true ->
          nil
      end

    %{
      date: date,
      season: season,
      competition: competition,
      round: round,
      stage: stage,
      home: team(r["home_team"] || r["Equipe_mandante"] || r["home"]),
      away: team(r["away_team"] || r["Equipe_visitante"] || r["away"]),
      home_goal: number(r["home_goal"] || r["Gols_mandante"]),
      away_goal: number(r["away_goal"] || r["Gols_visitante"]),
      source: file,
      details: r
    }
  end
end
