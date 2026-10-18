defmodule BrazilianSoccerMcp.Server do
  @moduledoc "A dependency-free stdio MCP server. Run with `mix mcp`."
  alias BrazilianSoccerMcp.JSON

  @doc "Escript entrypoint: starts the MCP server over standard input/output."
  def main(_args), do: run()

  def run do
    BrazilianSoccerMcp.load()

    IO.stream(:stdio, :line)
    |> Enum.each(fn line ->
      case JSON.decode(line) do
        {:ok, request} -> respond(request)
        _ -> :ok
      end
    end)
  end

  defp respond(%{"method" => "notifications/initialized"}), do: :ok

  defp respond(req) do
    response =
      case req["method"] do
        "initialize" ->
          {:result,
           %{
             protocolVersion: "2024-11-05",
             capabilities: %{tools: %{}},
             serverInfo: %{name: "brazilian-soccer", version: "0.1.0"}
           }}

        "tools/list" ->
          {:result, %{tools: tools()}}

        "tools/call" ->
          {:result, call(req["params"] || %{})}

        _ ->
          {:error, -32_601, "Method not found"}
      end

    if Map.has_key?(req, "id") do
      packet =
        case response do
          {:result, result} -> %{jsonrpc: "2.0", id: req["id"], result: result}
          {:error, code, message} -> %{jsonrpc: "2.0", id: req["id"], error: %{code: code, message: message}}
        end

      IO.puts(JSON.encode(packet))
    end
  end

  defp tools,
    do:
      Enum.map(
        [
          {"search_matches",
           "Search matches by team, season, competition, or from/to ISO dates."},
          {"team_stats", "Wins, losses and goals for a team."},
          {"head_to_head", "Compare two teams."},
          {"search_players", "Find FIFA players by name, club, nationality, or position."},
          {"standings", "Calculate league table from results."},
          {"aggregate_stats", "Goals and home-win aggregates."}
        ],
        fn {name, description} ->
          %{name: name, description: description, inputSchema: %{type: "object"}}
        end
      )

  defp call(%{"name" => name} = params) do
    args = params["arguments"] || %{}
    value =
      case name do
        "search_matches" ->
          BrazilianSoccerMcp.matches(args)

        "team_stats" ->
          BrazilianSoccerMcp.team_stats(args["team"], Map.delete(args, "team"))

        "head_to_head" ->
          BrazilianSoccerMcp.head_to_head(args["first_team"], args["second_team"], args)

        "search_players" ->
          BrazilianSoccerMcp.players(args)

        "standings" ->
          BrazilianSoccerMcp.standings(args["season"], args["competition"] || "Brasileirao")

        "aggregate_stats" ->
          BrazilianSoccerMcp.aggregate(args)

        _ ->
          %{error: "Unknown tool"}
      end

    %{content: [%{type: "text", text: JSON.encode(value)}]}
  rescue
    e -> %{content: [%{type: "text", text: "Error: #{Exception.message(e)}"}], isError: true}
  end
end
