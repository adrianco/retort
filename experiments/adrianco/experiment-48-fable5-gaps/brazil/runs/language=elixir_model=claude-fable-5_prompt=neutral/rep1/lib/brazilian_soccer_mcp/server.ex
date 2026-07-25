defmodule BrazilianSoccerMcp.Server do
  @moduledoc """
  MCP protocol layer: JSON-RPC 2.0 message handling for the stdio transport.

  Supports `initialize`, `notifications/initialized`, `ping`, `tools/list`,
  and `tools/call`. Pure functions — the transport loop lives in
  `BrazilianSoccerMcp.Stdio`.
  """

  alias BrazilianSoccerMcp.Tools

  @server_name "brazilian-soccer-mcp"
  @server_version "0.1.0"
  @supported_protocol_versions ["2025-06-18", "2025-03-26", "2024-11-05"]

  @doc """
  Handle one line of input. Returns `{:reply, json_binary}` or `:noreply`.
  """
  def handle_line(line) do
    case String.trim(line) do
      "" ->
        :noreply

      trimmed ->
        case JSON.decode(trimmed) do
          {:ok, message} ->
            handle_message(message)

          {:error, _} ->
            {:reply, encode_error(nil, -32700, "Parse error")}
        end
    end
  end

  @doc """
  Handle a decoded JSON-RPC message. Returns `{:reply, json_binary}` or `:noreply`.
  """
  def handle_message(%{"method" => method} = msg) do
    id = Map.get(msg, "id")
    params = Map.get(msg, "params", %{})

    cond do
      String.starts_with?(method, "notifications/") ->
        :noreply

      id == nil ->
        # A request without an id is a notification; nothing to answer.
        :noreply

      true ->
        case handle_request(method, params) do
          {:ok, result} -> {:reply, encode_result(id, result)}
          {:error, code, message} -> {:reply, encode_error(id, code, message)}
        end
    end
  end

  def handle_message(_other), do: {:reply, encode_error(nil, -32600, "Invalid Request")}

  defp handle_request("initialize", params) do
    requested = params["protocolVersion"]

    version =
      if requested in @supported_protocol_versions,
        do: requested,
        else: hd(@supported_protocol_versions)

    {:ok,
     %{
       protocolVersion: version,
       capabilities: %{tools: %{}},
       serverInfo: %{
         name: @server_name,
         title: "Brazilian Soccer Knowledge Base",
         version: @server_version
       }
     }}
  end

  defp handle_request("ping", _params), do: {:ok, %{}}

  defp handle_request("tools/list", _params), do: {:ok, %{tools: Tools.list()}}

  defp handle_request("tools/call", %{"name" => name} = params) do
    args = Map.get(params, "arguments", %{})

    case Tools.call(name, args) do
      {:ok, text} ->
        {:ok, %{content: [%{type: "text", text: text}], isError: false}}

      {:error, "unknown tool: " <> _ = message} ->
        {:error, -32602, message}

      {:error, message} ->
        # Tool-level failures are reported inside the result per the MCP spec.
        {:ok, %{content: [%{type: "text", text: "Error: " <> message}], isError: true}}
    end
  end

  defp handle_request("tools/call", _params), do: {:error, -32602, "missing tool name"}

  defp handle_request(method, _params), do: {:error, -32601, "Method not found: #{method}"}

  defp encode_result(id, result) do
    JSON.encode!(%{"jsonrpc" => "2.0", "id" => id, "result" => result})
  end

  defp encode_error(id, code, message) do
    JSON.encode!(%{
      "jsonrpc" => "2.0",
      "id" => id,
      "error" => %{"code" => code, "message" => message}
    })
  end
end
