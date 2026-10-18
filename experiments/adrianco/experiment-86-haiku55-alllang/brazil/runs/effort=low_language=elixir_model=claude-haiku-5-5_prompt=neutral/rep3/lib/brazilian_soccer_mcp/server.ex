defmodule BrazilianSoccerMcp.Server do
  @moduledoc """
  MCP server logic: JSON-RPC 2.0 request handling over newline-delimited JSON.

  Pure functions only. `handle_line/2` takes one raw input line and returns the
  encoded response, or `nil` when no response is due (notifications, blank lines).
  The transport lives in `BrazilianSoccerMcp.Stdio`.
  """

  alias BrazilianSoccerMcp.Tools

  @protocol_version "2024-11-05"
  @server_info %{name: "brazilian-soccer-mcp", version: "0.1.0"}

  @doc "Handles one input line and returns the JSON response, or `nil`."
  @spec handle_line(binary(), map()) :: binary() | nil
  def handle_line(line, data) do
    case String.trim(line) do
      "" ->
        nil

      trimmed ->
        case Jason.decode(trimmed) do
          {:ok, message} when is_map(message) -> message |> handle(data) |> encode()
          {:ok, _other} -> encode(error(nil, -32600, "Invalid Request"))
          {:error, _reason} -> encode(error(nil, -32700, "Parse error"))
        end
    end
  end

  @doc "Handles a decoded JSON-RPC message. Returns a response map, or `nil` for notifications."
  @spec handle(map(), map()) :: map() | nil
  def handle(%{"method" => method, "id" => id} = message, data) when not is_nil(id) do
    case dispatch(method, Map.get(message, "params") || %{}, data) do
      {:ok, result} -> %{jsonrpc: "2.0", id: id, result: result}
      {:error, code, text} -> error(id, code, text)
    end
  end

  def handle(%{"method" => _method}, _data), do: nil
  def handle(_message, _data), do: error(nil, -32600, "Invalid Request")

  defp dispatch("initialize", _params, _data) do
    {:ok,
     %{
       protocolVersion: @protocol_version,
       capabilities: %{tools: %{}},
       serverInfo: @server_info
     }}
  end

  defp dispatch("ping", _params, _data), do: {:ok, %{}}

  defp dispatch("tools/list", _params, _data), do: {:ok, %{tools: Tools.definitions()}}

  defp dispatch("tools/call", params, data) do
    name = params["name"]
    args = params["arguments"] || %{}

    case Tools.call(name, args, data) do
      {:ok, text} -> {:ok, tool_result(text, false)}
      {:error, text} -> {:ok, tool_result(text, true)}
    end
  end

  defp dispatch(method, _params, _data), do: {:error, -32601, "Method not found: #{method}"}

  defp tool_result(text, is_error) do
    %{content: [%{type: "text", text: text}], isError: is_error}
  end

  defp error(id, code, message) do
    %{jsonrpc: "2.0", id: id, error: %{code: code, message: message}}
  end

  defp encode(nil), do: nil
  defp encode(response), do: Jason.encode!(response)
end
