defmodule BrazilianSoccer.MCP.Server do
  @moduledoc """
  MCP (Model Context Protocol) JSON-RPC 2.0 request handling.

  Pure functions: `handle/1` takes a decoded request and returns the decoded
  response (or `nil` for notifications, which take no reply).  The transport
  lives in `BrazilianSoccer.MCP.Stdio`, which keeps this module trivially
  testable.

  Implemented methods: `initialize`, `ping`, `tools/list`, `tools/call`,
  `resources/list`, `resources/read`, `prompts/list` and the
  `notifications/*` family.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Format
  alias BrazilianSoccer.MCP.{JSON, Tools}
  alias BrazilianSoccer.Repo

  @supported_protocol_versions ["2025-06-18", "2025-03-26", "2024-11-05"]
  @latest_protocol_version "2025-06-18"

  @server_info %{
    "name" => "brazilian-soccer",
    "title" => "Brazilian Soccer Knowledge Graph",
    "version" => Mix.Project.config()[:version] || "1.0.0"
  }

  @instructions """
  Knowledge graph over six Brazilian football datasets: Campeonato Brasileiro
  Série A (2003-2023), Série B and C, Copa do Brasil, Copa Libertadores and the
  FIFA player database.

  Team names are normalised, so "Palmeiras", "Palmeiras-SP" and "Palmeiras - SP"
  all resolve to the same club; pass whatever spelling the user typed.
  Duplicate matches across the source files are merged, so counts are not
  double counted.

  Champions, standings and relegation are *derived from match results*, not
  read from an official table; the tools say so in their answers.
  """

  @error_codes %{
    parse_error: -32_700,
    invalid_request: -32_600,
    method_not_found: -32_601,
    invalid_params: -32_602,
    internal_error: -32_603
  }

  @doc "Handle one decoded JSON-RPC message. Returns a response map or `nil`."
  @spec handle(map | list) :: map | list | nil
  def handle(messages) when is_list(messages) do
    case Enum.map(messages, &handle/1) |> Enum.reject(&is_nil/1) do
      [] -> nil
      responses -> responses
    end
  end

  def handle(%{"method" => "notifications/" <> _}), do: nil

  def handle(%{"method" => method} = request) do
    id = Map.get(request, "id")
    params = Map.get(request, "params") || %{}

    # A request without an id is a notification: do the work, send nothing.
    case {dispatch(method, params), id} do
      {_, nil} -> nil
      {{:ok, result}, id} -> success(id, result)
      {{:error, code, message}, id} -> failure(id, code, message)
    end
  end

  def handle(%{"id" => id} = _malformed) when not is_nil(id) do
    failure(id, @error_codes.invalid_request, "invalid request: no method given")
  end

  def handle(_other), do: nil

  @doc "All method names this server implements."
  def methods do
    ~w(initialize ping tools/list tools/call resources/list resources/read prompts/list)
  end

  defp dispatch("initialize", params) do
    requested = Map.get(params, "protocolVersion")

    version =
      if requested in @supported_protocol_versions,
        do: requested,
        else: @latest_protocol_version

    {:ok,
     %{
       "protocolVersion" => version,
       "capabilities" => %{
         "tools" => %{"listChanged" => false},
         "resources" => %{"subscribe" => false, "listChanged" => false}
       },
       "serverInfo" => @server_info,
       "instructions" => @instructions
     }}
  end

  defp dispatch("ping", _params), do: {:ok, %{}}

  defp dispatch("tools/list", _params), do: {:ok, %{"tools" => Tools.list()}}

  defp dispatch("tools/call", params) do
    name = Map.get(params, "name")
    arguments = Map.get(params, "arguments") || %{}

    cond do
      not is_binary(name) ->
        {:error, @error_codes.invalid_params, "tools/call requires a tool name"}

      not is_map(arguments) ->
        {:error, @error_codes.invalid_params, "tool arguments must be an object"}

      true ->
        case safe_call(name, arguments) do
          {:ok, %{text: text, data: data}} ->
            {:ok,
             %{
               "content" => [%{"type" => "text", "text" => text}],
               "structuredContent" => data,
               "isError" => false
             }}

          {:error, message} ->
            # Tool level failures are reported inside the result, per the MCP
            # spec, so the model can read and recover from them.
            {:ok,
             %{
               "content" => [%{"type" => "text", "text" => message}],
               "isError" => true
             }}
        end
    end
  end

  defp dispatch("resources/list", _params), do: {:ok, %{"resources" => resources()}}

  defp dispatch("resources/read", params) do
    case read_resource(Map.get(params, "uri")) do
      {:ok, contents} -> {:ok, %{"contents" => [contents]}}
      :error -> {:error, @error_codes.invalid_params, "unknown resource: #{Map.get(params, "uri")}"}
    end
  end

  defp dispatch("prompts/list", _params), do: {:ok, %{"prompts" => []}}

  defp dispatch(method, _params) do
    {:error, @error_codes.method_not_found, "method not found: #{method}"}
  end

  defp safe_call(name, arguments) do
    Tools.call(name, arguments)
  rescue
    exception ->
      {:error, "Tool #{name} failed: #{Exception.message(exception)}"}
  catch
    :exit, reason -> {:error, "Tool #{name} exited: #{inspect(reason)}"}
  end

  # --- resources -----------------------------------------------------------

  @resources [
    %{
      uri: "brazilian-soccer://datasets",
      name: "datasets",
      title: "Source datasets",
      description: "The CSV files behind the graph, with row counts and licences.",
      mime_type: "text/markdown"
    },
    %{
      uri: "brazilian-soccer://competitions",
      name: "competitions",
      title: "Competitions and seasons",
      description: "Competitions in the graph and the seasons they cover.",
      mime_type: "text/markdown"
    },
    %{
      uri: "brazilian-soccer://teams",
      name: "teams",
      title: "Teams",
      description: "Canonical club names with the spellings found in the data.",
      mime_type: "text/markdown"
    },
    %{
      uri: "brazilian-soccer://sample-questions",
      name: "sample-questions",
      title: "Sample questions",
      description: "Questions this server can answer, with the tool to use.",
      mime_type: "text/markdown"
    }
  ]

  defp resources do
    Enum.map(@resources, fn resource ->
      %{
        "uri" => resource.uri,
        "name" => resource.name,
        "title" => resource.title,
        "description" => resource.description,
        "mimeType" => resource.mime_type
      }
    end)
  end

  defp read_resource(uri) do
    case Enum.find(@resources, &(&1.uri == uri)) do
      nil ->
        :error

      resource ->
        {:ok,
         %{
           "uri" => resource.uri,
           "mimeType" => resource.mime_type,
           "text" => resource_text(resource.name)
         }}
    end
  end

  defp resource_text("datasets") do
    graph = Repo.graph()
    Format.info(Map.put(graph.meta, :competitions, Graph.competitions()))
  end

  defp resource_text("competitions") do
    {:ok, result} = BrazilianSoccer.Query.Competitions.list(Repo.graph())
    Format.competitions(result)
  end

  defp resource_text("teams") do
    graph = Repo.graph()

    body =
      graph.teams
      |> Map.values()
      |> Enum.sort_by(&(-&1.match_count))
      |> Enum.take(80)
      |> Enum.map_join("\n", fn team ->
        "- #{team.name} (#{team.id}): #{team.match_count} matches; " <>
          "spellings: #{Enum.join(Enum.take(team.aliases, 4), ", ")}"
      end)

    "Teams by number of matches (top 80 of #{map_size(graph.teams)}):\n#{body}"
  end

  defp resource_text("sample-questions") do
    BrazilianSoccer.SampleQuestions.markdown()
  end

  defp success(id, result) do
    %{"jsonrpc" => "2.0", "id" => id, "result" => JSON.sanitize(result)}
  end

  defp failure(id, code, message) do
    %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
  end
end
