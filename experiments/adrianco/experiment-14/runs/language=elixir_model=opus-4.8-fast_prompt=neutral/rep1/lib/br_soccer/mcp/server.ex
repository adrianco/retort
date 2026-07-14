defmodule BrSoccer.MCP.Server do
  @moduledoc """
  Model Context Protocol server over stdio.

  Implements the JSON-RPC 2.0 methods an MCP client needs — `initialize`,
  `tools/list`, `tools/call`, `ping` — using newline-delimited JSON messages on
  stdin/stdout, as specified by the MCP stdio transport.

  `handle_message/1` is a pure function (string in, optional reply map out) so
  the protocol can be unit-tested without any I/O; `serve/0` is the runtime loop.
  """

  alias BrSoccer.MCP.Tools

  @protocol_version "2024-11-05"
  @server_info %{name: "br-soccer", version: "1.0.0"}

  @doc "Run the blocking stdio read/serve loop. Returns :ok on EOF."
  def serve do
    case IO.read(:stdio, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        log("stdin read error: #{inspect(reason)}")
        :ok

      line ->
        line |> String.trim() |> dispatch_line()
        serve()
    end
  end

  defp dispatch_line(""), do: :ok

  defp dispatch_line(line) do
    case handle_message(line) do
      {:reply, response} ->
        IO.puts(Jason.encode!(response))
        :ok

      :noreply ->
        :ok
    end
  end

  @doc """
  Handle a single raw JSON-RPC message string.

  Returns `{:reply, map}` for requests (which carry an `id`) and `:noreply` for
  notifications and unparseable input.
  """
  def handle_message(raw) when is_binary(raw) do
    case Jason.decode(raw) do
      {:ok, %{"method" => method} = msg} ->
        id = Map.get(msg, "id")
        params = Map.get(msg, "params", %{})
        route(method, params, id)

      {:ok, _other} ->
        :noreply

      {:error, _} ->
        :noreply
    end
  end

  # Notifications (no id) never get a response.
  defp route("notifications/" <> _, _params, _id), do: :noreply

  defp route("initialize", _params, id) do
    reply(id, %{
      protocolVersion: @protocol_version,
      capabilities: %{tools: %{}},
      serverInfo: @server_info,
      instructions:
        "Query Brazilian soccer data: matches, head-to-head, team records, " <>
          "league standings, FIFA players and aggregate statistics."
    })
  end

  defp route("ping", _params, id), do: reply(id, %{})

  defp route("tools/list", _params, id) do
    reply(id, %{tools: Tools.list()})
  end

  defp route("tools/call", params, id) do
    name = Map.get(params, "name")
    args = Map.get(params, "arguments", %{})

    case Tools.call(name, args) do
      {:ok, text} ->
        reply(id, %{content: [%{type: "text", text: text}], isError: false})

      {:error, message} ->
        reply(id, %{content: [%{type: "text", text: message}], isError: true})
    end
  end

  defp route(_unknown, _params, nil), do: :noreply

  defp route(method, _params, id) do
    error(id, -32601, "Method not found: #{method}")
  end

  # ---- JSON-RPC envelope helpers ----

  defp reply(nil, _result), do: :noreply

  defp reply(id, result) do
    {:reply, %{jsonrpc: "2.0", id: id, result: result}}
  end

  defp error(nil, _code, _message), do: :noreply

  defp error(id, code, message) do
    {:reply, %{jsonrpc: "2.0", id: id, error: %{code: code, message: message}}}
  end

  defp log(msg), do: IO.puts(:stderr, "[br-soccer] " <> msg)
end
