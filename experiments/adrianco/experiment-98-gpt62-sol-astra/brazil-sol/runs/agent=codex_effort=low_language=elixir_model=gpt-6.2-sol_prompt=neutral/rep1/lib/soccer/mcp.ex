defmodule Soccer.MCP do
  @moduledoc "Read-only MCP server using newline-delimited JSON-RPC over stdio."
  alias Soccer.{Data, Query}

  @versions ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
  @match_sources ~w(Brasileirao_Matches.csv Brazilian_Cup_Matches.csv Libertadores_Matches.csv BR-Football-Dataset.csv novo_campeonato_brasileiro.csv)

  def main(args) do
    case args do
      [] ->
        serve(System.get_env("SOCCER_DATA_DIR") || "data/kaggle")

      ["--data-dir", directory] ->
        serve(directory)

      _ ->
        IO.puts(:stderr, "Usage: soccer [--data-dir PATH]")
        System.halt(2)
    end
  end

  defp serve(directory) do
    :ok = :io.setopts(:standard_io, encoding: :unicode)
    data = Data.load!(directory)

    for line <- IO.stream(:stdio, :line) do
      case handle_line(data, line) do
        nil -> :ok
        response -> IO.puts(JSON.encode!(response))
      end
    end
  end

  def handle_line(data, line) do
    case JSON.decode(line) do
      {:ok, message} -> handle(data, message)
      {:error, _} -> error(nil, -32700, "Parse error")
    end
  end

  def handle(data, %{"jsonrpc" => "2.0", "method" => method, "id" => id} = message)
      when is_binary(method) and (is_binary(id) or is_integer(id)) do
    case dispatch(data, method, Map.get(message, "params", %{})) do
      {:ok, result} -> %{jsonrpc: "2.0", id: id, result: result}
      {:error, code, reason} -> error(id, code, reason)
    end
  end

  def handle(_, %{"jsonrpc" => "2.0", "method" => method} = notification)
      when is_binary(method) and not is_map_key(notification, "id"), do: nil

  def handle(_, _), do: error(nil, -32600, "Invalid request")

  defp dispatch(_, _, params) when not is_map(params),
    do: {:error, -32602, "Expected a params object"}

  defp dispatch(_, "initialize", %{"protocolVersion" => version}) when is_binary(version) do
    {:ok,
     %{
       protocolVersion: if(version in @versions, do: version, else: hd(@versions)),
       capabilities: %{tools: %{}},
       serverInfo: %{name: "brazilian-soccer", version: "1.0.0"},
       instructions:
         "Use these tools to answer Brazilian soccer questions from the supplied datasets. " <>
           "Call find_matches for scores and head-to-head, team_profile for records and FIFA roster, " <>
           "and competition for standings or brackets. Reuse the conversation's fixture filters for score follow-ups. " <>
           "FIFA club affiliations are a historical snapshot. List tools return total and next_offset for pagination."
     }}
  end

  defp dispatch(_, "initialize", _), do: {:error, -32602, "Expected protocolVersion"}
  defp dispatch(_, "ping", _), do: {:ok, %{}}
  defp dispatch(_, "tools/list", _), do: {:ok, %{tools: tools()}}

  defp dispatch(data, "tools/call", %{"name" => name} = params) do
    args = Map.get(params, "arguments", %{})

    case Enum.find(tools(), &(&1.name == name)) do
      nil ->
        {:error, -32602, "Unknown tool"}

      tool ->
        case validate(tool.inputSchema, args) do
          :ok ->
            result = call(data, name, args)

            {:ok,
             %{structuredContent: result, content: [%{type: "text", text: JSON.encode!(result)}]}}

          {:error, message} ->
            {:ok, %{isError: true, content: [%{type: "text", text: message}]}}
        end
    end
  end

  defp dispatch(_, "tools/call", _), do: {:error, -32602, "Expected a tool name"}
  defp dispatch(_, _, _), do: {:error, -32601, "Method not found"}

  defp call(data, "find_matches", args), do: Query.matches(data, args)
  defp call(data, "team_profile", args), do: Query.team(data, args)
  defp call(data, "find_players", args), do: Query.players(data, args)
  defp call(data, "competition", args), do: Query.competition(data, args)
  defp call(data, "statistics", args), do: Query.statistics(data, args)
  defp call(data, "data_sources", _), do: %{row_counts: data.counts}

  def tools do
    paging = %{
      "limit" => integer("Page size. Defaults to 20.", 1, 200),
      "offset" => integer("Zero-based starting offset.", 0)
    }

    filters = %{
      "team" => string("Club name or alias."),
      "opponent" => string("Second club for a head-to-head query. Requires team."),
      "venue" =>
        choice("Which side the selected team played on. Requires team.", ~w(home away either)),
      "competition" =>
        string("Brasileirão (Série A), Série B, Série C, Copa do Brasil, or Copa Libertadores."),
      "season" =>
        integer("Competition edition year, which can differ from the match date.", 1900, 2200),
      "seasons" => %{type: "array", items: integer("Edition year.", 1900, 2200), minItems: 1},
      "from" => string("Inclusive start date in YYYY-MM-DD or DD/MM/YYYY format."),
      "to" => string("Inclusive end date in YYYY-MM-DD or DD/MM/YYYY format."),
      "round" => integer("Numeric match round.", 1),
      "stage" => string("Tournament stage, such as final, semifinals or group stage."),
      "derbies" => boolean("Restrict to the supported traditional rivalries."),
      "source" =>
        choice("Query the rows of one CSV instead of the reconciled fixtures.", @match_sources)
    }

    players = %{
      "name" => string("Full or partial FIFA display name, ignoring accents and case."),
      "nationality" => string("Nationality, for example Brazil or Brazilian."),
      "club" => string("Club name or alias."),
      "position" => string("FIFA position code or role, such as forwards or midfielders."),
      "min_overall" => integer("Minimum FIFA overall rating.", 0, 100),
      "attributes" =>
        boolean(
          "Include the original FIFA attribute fields, including skills and physical attributes."
        ),
      "brazilian_clubs" =>
        boolean(
          "Restrict to clubs in the Brazilian domestic match data and return counts and average ratings by club."
        )
    }

    [
      tool(
        "find_matches",
        "Find fixtures, scores, extended match statistics, derbies and head-to-head records. Newest fixtures are first. Use limit 1 for the last meeting.",
        Map.merge(filters, paging)
      ),
      tool(
        "team_profile",
        "Join match history, home and away records, performance by competition and season, and the FIFA roster through a shared club identity.",
        Map.merge(filters, paging),
        ["team"]
      ),
      tool(
        "find_players",
        "Search and rank the FIFA snapshot by overall rating. Club affiliations and ratings reflect the dataset.",
        Map.merge(players, paging)
      ),
      tool(
        "competition",
        "Find a season's results or bracket, calculate league standings, identify the score-derived champion or relegation places, or check player scorer availability.",
        filters
        |> Map.take(~w(competition season stage round source))
        |> Map.merge(paging)
        |> Map.put(
          "view",
          choice(
            "Defaults to standings. Use results for schedules and scores.",
            ~w(standings results bracket champion relegation top_scorers)
          )
        ),
        ~w(competition season)
      ),
      tool(
        "statistics",
        "Calculate average goals, win rates, season trends, biggest victories and team rankings.",
        filters
        |> Map.merge(paging)
        |> Map.merge(%{
          "view" =>
            choice(
              "Defaults to summary.",
              ~w(summary biggest_wins seasons best_home best_away most_goals)
            ),
          "min_matches" =>
            integer("Minimum scored appearances for team rankings. Defaults to 1.", 1)
        })
      ),
      tool("data_sources", "List all six datasets and their loaded row counts.", %{})
    ]
  end

  defp tool(name, description, properties, required \\ []) do
    %{
      name: name,
      description: description,
      annotations: %{readOnlyHint: true},
      inputSchema: %{
        type: "object",
        properties: properties,
        required: required,
        additionalProperties: false
      }
    }
  end

  defp string(description), do: %{type: "string", description: description, minLength: 1}
  defp choice(description, options), do: Map.put(string(description), :enum, options)
  defp boolean(description), do: %{type: "boolean", description: description}

  defp integer(description, minimum),
    do: %{type: "integer", description: description, minimum: minimum}

  defp integer(description, minimum, maximum),
    do: Map.put(integer(description, minimum), :maximum, maximum)

  defp validate(schema, args) when is_map(args) do
    missing = Enum.find(schema.required, &(not Map.has_key?(args, &1)))
    invalid = Enum.find(args, fn {key, value} -> not valid?(schema.properties[key], value) end)
    from = args["from"]
    to = args["to"]

    cond do
      missing ->
        {:error, "Missing required argument: #{missing}"}

      invalid ->
        {:error, "Invalid argument: #{elem(invalid, 0)}"}

      (args["opponent"] || args["venue"]) && !args["team"] ->
        {:error, "Specify team with opponent or venue."}

      from && !Data.date(from) ->
        {:error, "Invalid start date."}

      to && !Data.date(to) ->
        {:error, "Invalid end date."}

      from && to && Data.date(from) > Data.date(to) ->
        {:error, "Start date must precede or equal end date."}

      true ->
        :ok
    end
  end

  defp validate(_, _), do: {:error, "Expected an arguments object."}

  defp valid?(%{type: "string", enum: options}, value), do: value in options
  defp valid?(%{type: "string"}, value), do: is_binary(value) and String.trim(value) != ""
  defp valid?(%{type: "boolean"}, value), do: is_boolean(value)

  defp valid?(%{type: "integer", minimum: min} = spec, value),
    do: is_integer(value) and value >= min and (!spec[:maximum] || value <= spec.maximum)

  defp valid?(%{type: "array", items: spec}, value),
    do: is_list(value) and value != [] and Enum.all?(value, &valid?(spec, &1))

  defp valid?(_, _), do: false

  defp error(id, code, message),
    do: %{jsonrpc: "2.0", id: id, error: %{code: code, message: message}}
end
