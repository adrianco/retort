defmodule BrazilianSoccerMcp.MCP do
  @moduledoc "JSON-RPC 2.0 MCP server over stdio. Run with `mix run --no-halt`."
  alias BrazilianSoccerMcp.{JSON, Query, Store}

  @tool_descriptions [
    {"search_matches", "Find matches by team, date range, competition, season, or stage."},
    {"team_statistics", "Calculate wins, draws, losses, and goals for one team."},
    {"compare_teams", "Calculate head-to-head results between two teams."},
    {"search_players", "Find FIFA players by name, nationality, club, or position."},
    {"standings", "Calculate a competition table from match results."},
    {"competition_statistics", "Calculate goals, result distribution, and biggest wins."},
    {"catalog_summary", "Report loaded source coverage and record counts."}
  ]
  defp tool(name, description),
    do: %{
      "name" => name,
      "description" => description,
      "inputSchema" => %{"type" => "object", "additionalProperties" => true}
    }

  def run do
    IO.stream(:stdio, :line) |> Enum.each(fn line -> line |> handle_line() |> maybe_write() end)
  end

  def handle_line(line) do
    case JSON.decode(line) do
      {:ok, request} -> handle(request)
      {:error, _} -> error(nil, -32700, "Parse error")
    end
  end

  def handle(%{"method" => "initialize", "id" => id}),
    do:
      response(id, %{
        "protocolVersion" => "2024-11-05",
        "serverInfo" => %{"name" => "brazilian-soccer-mcp", "version" => "0.1.0"},
        "capabilities" => %{"tools" => %{}}
      })

  def handle(%{"method" => "notifications/initialized"}), do: nil

  def handle(%{"method" => "tools/list", "id" => id}),
    do:
      response(id, %{
        "tools" =>
          Enum.map(@tool_descriptions, fn {name, description} -> tool(name, description) end)
      })

  def handle(%{"method" => "resources/list", "id" => id}),
    do:
      response(id, %{
        "resources" => [
          %{
            "uri" => "brazilian-soccer://catalog",
            "name" => "Brazilian soccer catalog",
            "description" => "Summary of the supplied Kaggle match and FIFA player datasets.",
            "mimeType" => "application/json"
          }
        ]
      })

  def handle(%{
        "method" => "resources/read",
        "id" => id,
        "params" => %{"uri" => "brazilian-soccer://catalog"}
      }),
      do: response(id, resource_contents())

  def handle(%{"method" => "tools/call", "id" => id, "params" => %{"name" => name} = params}),
    do: response(id, call_tool(name, Map.get(params, "arguments", %{})))

  def handle(%{"id" => id}), do: error(id, -32601, "Method not found")
  def handle(_), do: nil

  defp call_tool(name, arguments) do
    with {:ok, catalog} <- Store.catalog() do
      result =
        case name do
          "search_matches" ->
            Query.matches(catalog, arguments)

          "team_statistics" ->
            Query.team_statistics(catalog, required(arguments, "team"), arguments)

          "compare_teams" ->
            Query.head_to_head(
              catalog,
              required(arguments, "team_a"),
              required(arguments, "team_b"),
              arguments
            )

          "search_players" ->
            Query.players(catalog, arguments)

          "standings" ->
            Query.standings(
              catalog,
              required(arguments, "season"),
              Map.get(arguments, "competition", "Brasileirão")
            )

          "competition_statistics" ->
            Query.competition_statistics(catalog, arguments)

          "catalog_summary" ->
            %{
              matches: length(catalog.matches),
              players: length(catalog.players),
              sources: catalog.matches |> Enum.map(& &1.source) |> Enum.uniq()
            }

          _ ->
            throw({:tool_error, "Unknown tool: #{name}"})
        end

      %{"content" => [%{"type" => "text", "text" => JSON.encode(result)}]}
    else
      {:error, reason} ->
        %{
          "content" => [%{"type" => "text", "text" => "Unable to load data: #{inspect(reason)}"}],
          "isError" => true
        }
    end
  catch
    {:tool_error, message} ->
      %{"content" => [%{"type" => "text", "text" => message}], "isError" => true}
  end

  defp required(arguments, key), do: Map.fetch!(arguments, key)

  defp resource_contents do
    case Store.catalog() do
      {:ok, catalog} ->
        summary = %{
          matches: length(catalog.matches),
          players: length(catalog.players),
          sources: catalog.matches |> Enum.map(& &1.source) |> Enum.uniq()
        }

        %{
          "contents" => [
            %{
              "uri" => "brazilian-soccer://catalog",
              "mimeType" => "application/json",
              "text" => JSON.encode(summary)
            }
          ]
        }

      {:error, reason} ->
        %{
          "contents" => [
            %{
              "uri" => "brazilian-soccer://catalog",
              "mimeType" => "text/plain",
              "text" => "Unable to load data: #{inspect(reason)}"
            }
          ]
        }
    end
  end

  defp response(id, result), do: %{"jsonrpc" => "2.0", "id" => id, "result" => result}

  defp error(id, code, message),
    do: %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}

  defp maybe_write(nil), do: :ok
  defp maybe_write(message), do: IO.puts(JSON.encode(message))
end
