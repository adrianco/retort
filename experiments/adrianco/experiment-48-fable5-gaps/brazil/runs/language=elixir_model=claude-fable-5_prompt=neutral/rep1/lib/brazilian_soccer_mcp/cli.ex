defmodule BrazilianSoccerMcp.CLI do
  @moduledoc """
  escript entry point: `./brazilian_soccer_mcp [--data-dir DIR]` starts the
  MCP server on stdio.
  """

  def main(argv) do
    {opts, _rest, _invalid} = OptionParser.parse(argv, strict: [data_dir: :string])
    BrazilianSoccerMcp.Stdio.start(opts[:data_dir])
  end
end
