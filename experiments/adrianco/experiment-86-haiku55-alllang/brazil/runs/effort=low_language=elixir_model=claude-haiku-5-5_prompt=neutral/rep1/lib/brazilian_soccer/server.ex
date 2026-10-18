defmodule BrazilianSoccer.Server do
  @moduledoc """
  JSON-RPC 2.0 handling for the Model Context Protocol (stdio transport).

  Supports `initialize`, `ping`, `tools/list` and `tools/call`. Notifications
  (requests without an `id`) get no response. Tool failures are returned as
  results with `isError: true`, as the MCP spec requires; protocol failures
  use JSON-RPC error objects.

  Functions here are pure: they take the decoded request and the loaded
  dataset and return the response map (or `nil`).
  """

  alias BrazilianSoccer.Tools

  @protocol_version "2024-11-05"
  @server_info %{name: "brazilian-soccer", version: "0.1.0"}

  @parse_error -32_700
  @invalid_request -32_600
  @method_not_found -32_601
  @invalid_params -32_602

  @doc "Handles one line of input. Returns the encoded response or `nil`."
  @spec handle_line(binary(), BrazilianSoccer.Data.t()) :: map() | nil
  def handle_line(line, data) do
    case JSON.decode(line) do
      {:ok, %{} = message} -> handle(message, data)
      {:ok, _other} -> error(nil, @invalid_request, "Request must be a JSON object")
      {:error, _} -> error(nil, @parse_error, "Parse error")
    end
  end

  @doc "Handles a decoded JSON-RPC message. Returns the response map or `nil`."
  @spec handle(map(), BrazilianSoccer.Data.t()) :: map() | nil
  def handle(%{"jsonrpc" => "2.0", "method" => method} = message, data) when is_binary(method) do
    if Map.has_key?(message, "id") do
      case dispatch(method, Map.get(message, "params") || %{}, data) do
        {:ok, result} -> %{jsonrpc: "2.0", id: message["id"], result: result}
        {:error, code, text} -> error(message["id"], code, text)
      end
    end
  end

  def handle(message, _data) do
    if Map.has_key?(message, "id"),
      do: error(message["id"], @invalid_request, "Invalid Request"),
      else: nil
  end

  defp dispatch("initialize", _params, _data) do
    {:ok,
     %{
       protocolVersion: @protocol_version,
       capabilities: %{tools: %{}},
       serverInfo: @server_info
     }}
  end

  defp dispatch("ping", _params, _data), do: {:ok, %{}}

  defp dispatch("tools/list", _params, _data), do: {:ok, %{tools: Tools.list()}}

  defp dispatch("tools/call", %{"name" => name} = params, data) when is_binary(name) do
    args = Map.get(params, "arguments") || %{}

    case Tools.call(name, args, data) do
      {:ok, text} -> {:ok, tool_result(text, false)}
      {:error, text} -> {:ok, tool_result(text, true)}
    end
  end

  defp dispatch("tools/call", _params, _data),
    do: {:error, @invalid_params, "tools/call requires a string 'name'"}

  defp dispatch(method, _params, _data),
    do: {:error, @method_not_found, "Method not found: #{method}"}

  defp tool_result(text, is_error) do
    %{content: [%{type: "text", text: text}], isError: is_error}
  end

  defp error(id, code, text) do
    %{jsonrpc: "2.0", id: id, error: %{code: code, message: text}}
  end
end
