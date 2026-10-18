defmodule SoccerMcp.Server do
  @moduledoc """
  JSON-RPC 2.0 handling for the Model Context Protocol (stdio transport).

  `handle_line/2` takes one raw line from the client and returns the encoded
  response line, or `nil` when no response is due (notifications). It has no
  side effects, so the protocol can be tested without a process or a pipe.
  """

  alias SoccerMcp.Tools

  @protocol_version "2024-11-05"
  @server_name "brazilian-soccer-mcp"
  @server_version "0.1.0"

  @parse_error -32_700
  @invalid_request -32_600
  @method_not_found -32_601
  @invalid_params -32_602

  @doc "Handles one line of input and returns the response line, or `nil`."
  @spec handle_line(String.t(), SoccerMcp.Store.t()) :: String.t() | nil
  def handle_line(line, store) do
    case Jason.decode(line) do
      {:ok, message} when is_map(message) ->
        message |> handle(store) |> encode()

      {:ok, _other} ->
        error_response(nil, @invalid_request, "request must be a JSON object") |> encode()

      {:error, _} ->
        error_response(nil, @parse_error, "parse error") |> encode()
    end
  end

  @doc "Handles a decoded JSON-RPC message and returns a response map, or `nil`."
  @spec handle(map(), SoccerMcp.Store.t()) :: map() | nil
  def handle(%{"method" => method} = message, store) when is_binary(method) do
    case Map.fetch(message, "id") do
      # Notifications carry no id and get no response.
      :error -> nil
      {:ok, id} -> dispatch(id, method, Map.get(message, "params") || %{}, store)
    end
  end

  def handle(message, _store) do
    error_response(Map.get(message, "id"), @invalid_request, "missing method")
  end

  defp dispatch(id, "initialize", _params, _store) do
    result(id, %{
      protocolVersion: @protocol_version,
      capabilities: %{tools: %{}},
      serverInfo: %{name: @server_name, version: @server_version},
      instructions:
        "Answers questions about Brazilian soccer: Brasileirão, Copa do Brasil and Libertadores matches (2003-2023), team records, standings, and FIFA player ratings."
    })
  end

  defp dispatch(id, "ping", _params, _store), do: result(id, %{})

  defp dispatch(id, "tools/list", _params, _store) do
    result(id, %{tools: Tools.definitions()})
  end

  defp dispatch(id, "tools/call", %{"name" => name} = params, store) when is_binary(name) do
    arguments = Map.get(params, "arguments") || %{}

    case Tools.call(name, arguments, store) do
      {:ok, text} -> result(id, tool_content(text, false))
      {:error, text} -> result(id, tool_content(text, true))
    end
  end

  defp dispatch(id, "tools/call", _params, _store) do
    error_response(id, @invalid_params, "tools/call requires a tool name")
  end

  defp dispatch(id, method, _params, _store) do
    error_response(id, @method_not_found, "method not found: #{method}")
  end

  defp tool_content(text, is_error) do
    %{content: [%{type: "text", text: text}], isError: is_error}
  end

  defp result(id, value), do: %{jsonrpc: "2.0", id: id, result: value}

  defp error_response(id, code, message) do
    %{jsonrpc: "2.0", id: id, error: %{code: code, message: message}}
  end

  defp encode(nil), do: nil
  defp encode(response), do: Jason.encode!(response)
end
