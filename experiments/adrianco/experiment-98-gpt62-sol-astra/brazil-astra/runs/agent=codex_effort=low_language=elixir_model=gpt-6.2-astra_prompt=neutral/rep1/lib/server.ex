defmodule Soccer.Server do
  alias Soccer.{Data, Query}
  @string %{type: "string"}
  @page %{
    "limit" => %{type: "integer", minimum: 1, maximum: 100},
    "offset" => %{type: "integer", minimum: 0}
  }
  @filters %{
    "team" => @string,
    "opponent" => @string,
    "venue" => %{enum: ["home", "away"], type: "string"},
    "competition" => %{
      type: "string",
      description: "Brasileirão (Serie A), Serie B, Serie C, Copa do Brasil, or Libertadores"
    },
    "source" => %{
      type: "string",
      enum:
        ~w(Brasileirao_Matches Brazilian_Cup_Matches Libertadores_Matches BR-Football-Dataset novo_campeonato_brasileiro),
      description: "Restrict to original rows from one dataset."
    },
    "season" => %{type: "integer"},
    "stage" => %{
      type: "string",
      description: "Round number or stage, e.g. final, quarterfinals, round of 16"
    },
    "derby" => %{type: "boolean", description: "Limit to curated traditional rivalries."},
    "from" => %{type: "string", format: "date"},
    "to" => %{type: "string", format: "date"}
  }
  @definitions [
    {"team_profile",
     "Join a team’s competition record and latest five fixtures to its five highest-rated FIFA players. The FIFA snapshot is independent of match season.",
     Map.take(@filters, ["team", "season", "competition"])},
    {"matches",
     "Find fixtures, scores and source attributes, latest first. For head-to-head use team and opponent. Use stage for cup brackets and finals.",
     Map.merge(@filters, @page)},
    {"players",
     "Search FIFA players by partial name or club, nationality (Brazil), and position (e.g. LW or forward). Returns all attributes in descending overall rating. Use a club as team in matches for its fixtures.",
     Map.merge(Map.new(~w(name club nationality position), &{&1, @string}), @page)},
    {"statistics",
     "Calculate goals per match, home win percentage and team W/D/L. Group by season for trends, venue for home/away splits, competition for participation.",
     Map.put(@filters, "group_by", %{type: "string", enum: ~w(season venue competition)})},
    {"standings",
     "Rank teams by match points, goals or win rate. For league tables select competition and season. Use margin to rank individual wins. Tables reflect dataset results only. Individual scorers are unavailable.",
     Map.merge(Map.merge(@filters, @page), %{
       "rank_by" => %{type: "string", enum: ~w(points goals win_rate margin)}
     })}
  ]
  def main(args) do
    dir =
      List.first(args) ||
        Path.expand("data/kaggle", Path.dirname(to_string(:escript.script_name())))

    db = Data.load(dir)

    IO.stream(:stdio, :line)
    |> Enum.each(fn line ->
      if response = process(line, db), do: IO.puts(JSON.encode!(response))
    end)
  end

  def process(line, db) do
    case JSON.decode(line) do
      {:ok, %{"jsonrpc" => "2.0", "method" => method} = msg} when is_binary(method) ->
        if Map.has_key?(msg, "id") do
          base = %{jsonrpc: "2.0", id: msg["id"]}

          case dispatch(method, Map.get(msg, "params", %{}), db) do
            {:error, code, message} -> Map.put(base, :error, %{code: code, message: message})
            value -> Map.put(base, :result, value)
          end
        end

      {:ok, _} ->
        error(-32600, "Invalid Request")

      _ ->
        error(-32700, "Parse error")
    end
  end

  defp error(code, msg), do: %{jsonrpc: "2.0", id: nil, error: %{code: code, message: msg}}

  defp dispatch("initialize", p, _) when is_map(p) do
    versions = ~w(2025-06-18 2025-03-26 2024-11-05)

    %{
      protocolVersion:
        if(p["protocolVersion"] in versions, do: p["protocolVersion"], else: hd(versions)),
      capabilities: %{tools: %{}},
      serverInfo: %{name: "brazilian-soccer", version: "1.0.0"}
    }
  end

  defp dispatch("ping", _, _), do: %{}

  defp dispatch("tools/list", _, _) do
    %{
      tools:
        for(
          {name, description, props} <- @definitions,
          do: %{
            name: name,
            description: description,
            inputSchema: %{
              type: "object",
              properties: props,
              required: if(name == "team_profile", do: ["team"], else: []),
              additionalProperties: false
            }
          }
        )
    }
  end

  defp dispatch("tools/call", %{"name" => name} = p, db) do
    case List.keyfind(@definitions, name, 0) do
      nil ->
        {:error, -32602, "Unknown tool"}

      {_, _, props} ->
        a = Map.get(p, "arguments", %{})

        with :ok <- validate(a, props),
             true <- name != "team_profile" or Map.has_key?(a, "team") do
          result = Query.run(db, name, a)
          %{content: [%{type: "text", text: JSON.encode!(result)}]}
        else
          false -> %{isError: true, content: [%{type: "text", text: "team is required"}]}
          {:error, msg} -> %{isError: true, content: [%{type: "text", text: msg}]}
        end
    end
  end

  defp dispatch(method, _, _) when method in ["initialize", "tools/call"],
    do: {:error, -32602, "Invalid params"}

  defp dispatch(_, _, _), do: {:error, -32601, "Method not found"}

  defp validate(a, props) when is_map(a) do
    invalid = Enum.find(a, fn {key, v} -> !valid?(props[key], v) end)

    cond do
      invalid -> {:error, "Invalid argument " <> elem(invalid, 0)}
      a["from"] && a["to"] && a["from"] > a["to"] -> {:error, "from must precede or equal to"}
      a["group_by"] == "venue" && !a["team"] -> {:error, "venue grouping requires team"}
      a["opponent"] && !a["team"] -> {:error, "opponent requires team"}
      true -> :ok
    end
  end

  defp validate(_, _), do: {:error, "arguments must be an object"}
  defp valid?(%{enum: values}, v), do: v in values
  defp valid?(%{format: "date"}, v), do: is_binary(v) and match?({:ok, _}, Date.from_iso8601(v))

  defp valid?(%{type: "integer"} = s, v),
    do: is_integer(v) and v >= Map.get(s, :minimum, v) and v <= Map.get(s, :maximum, v)

  defp valid?(%{type: "string"}, v), do: is_binary(v) and String.trim(v) != ""
  defp valid?(%{type: "boolean"}, v), do: is_boolean(v)
  defp valid?(_, _), do: false
end
