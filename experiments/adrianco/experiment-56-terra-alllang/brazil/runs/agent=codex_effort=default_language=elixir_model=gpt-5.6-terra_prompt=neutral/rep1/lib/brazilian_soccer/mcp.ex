defmodule BrazilianSoccer.MCP do
  @moduledoc "A stdio JSON-RPC MCP server. Run with `mix escript.build && ./brazilian_soccer`."
  alias BrazilianSoccer.{JSON, Normalize}

  @tools [
    %{
      name: "search_matches",
      description:
        "Search matches by team, opponent, season, competition, dates, stage, or venue.",
      inputSchema: %{
        type: "object",
        properties: %{
          team: %{type: "string"},
          opponent: %{type: "string"},
          season: %{type: "integer"},
          competition: %{type: "string"},
          from: %{type: "string"},
          to: %{type: "string"},
          limit: %{type: "integer"}
        }
      }
    },
    %{
      name: "team_statistics",
      description: "Calculate a team's W/D/L and goals record.",
      inputSchema: %{
        type: "object",
        required: ["team"],
        properties: %{
          team: %{type: "string"},
          season: %{type: "integer"},
          competition: %{type: "string"},
          venue: %{type: "string"}
        }
      }
    },
    %{
      name: "head_to_head",
      description: "Compare two teams' results.",
      inputSchema: %{
        type: "object",
        required: ["first", "second"],
        properties: %{first: %{type: "string"}, second: %{type: "string"}}
      }
    },
    %{
      name: "search_players",
      description: "Search FIFA player records.",
      inputSchema: %{
        type: "object",
        properties: %{
          name: %{type: "string"},
          nationality: %{type: "string"},
          club: %{type: "string"},
          position: %{type: "string"},
          min_overall: %{type: "integer"},
          limit: %{type: "integer"}
        }
      }
    },
    %{
      name: "standings",
      description: "Calculate league standings from match results.",
      inputSchema: %{
        type: "object",
        required: ["season"],
        properties: %{season: %{type: "integer"}, competition: %{type: "string"}}
      }
    },
    %{
      name: "competition_statistics",
      description: "Calculate aggregate goals and result statistics.",
      inputSchema: %{
        type: "object",
        properties: %{season: %{type: "integer"}, competition: %{type: "string"}}
      }
    }
  ]
  def main(_args), do: serve(BrazilianSoccer.load())

  def serve(data) do
    IO.stream(:stdio, :line)
    |> Enum.each(fn line ->
      case safe_decode(line) do
        {:ok, request} -> respond(request, data)
        _ -> :ok
      end
    end)
  end

  defp safe_decode(line) do
    try do
      {:ok, JSON.decode!(line)}
    rescue
      _ -> :error
    end
  end

  defp respond(%{"method" => "notifications/initialized"}, _), do: :ok

  defp respond(%{"method" => "initialize", "id" => id}, _),
    do:
      output(id, %{
        protocolVersion: "2025-03-26",
        capabilities: %{tools: %{}},
        serverInfo: %{name: "brazilian-soccer", version: "0.1.0"}
      })

  defp respond(%{"method" => "tools/list", "id" => id}, _), do: output(id, %{tools: @tools})

  defp respond(
         %{"method" => "tools/call", "id" => id, "params" => %{"name" => name} = params},
         data
       ) do
    args = Map.get(params, "arguments", %{})
    result = call(name, args, data)

    output(id, %{
      content: [%{type: "text", text: inspect(result, pretty: true, limit: :infinity)}],
      structuredContent: result
    })
  rescue
    e -> output(id, %{content: [%{type: "text", text: Exception.message(e)}], isError: true})
  end

  defp respond(%{"id" => id}, _),
    do: output(id, %{error: %{code: -32601, message: "Method not found"}})

  defp respond(_, _), do: :ok
  defp call("search_matches", args, data), do: BrazilianSoccer.search_matches(data, opts(args))

  defp call("team_statistics", %{"team" => team} = args, data),
    do: BrazilianSoccer.team_statistics(data, team, opts(Map.delete(args, "team")))

  defp call("head_to_head", %{"first" => a, "second" => b} = args, data),
    do: BrazilianSoccer.head_to_head(data, a, b, opts(Map.drop(args, ["first", "second"])))

  defp call("search_players", args, data), do: BrazilianSoccer.search_players(data, opts(args))

  defp call("standings", %{"season" => season} = args, data),
    do: BrazilianSoccer.standings(data, season, opts(Map.delete(args, "season")))

  defp call("competition_statistics", args, data),
    do: BrazilianSoccer.competition_statistics(data, opts(args))

  defp call(name, _, _), do: raise(ArgumentError, "unknown tool #{name}")

  defp opts(args),
    do: args |> Enum.map(fn {k, v} -> {String.to_existing_atom(k), convert(k, v)} end)

  defp convert("venue", v) when is_binary(v), do: String.to_existing_atom(Normalize.text(v))
  defp convert(_, v), do: v
  defp output(id, result), do: IO.puts(JSON.encode(%{jsonrpc: "2.0", id: id, result: result}))
end
