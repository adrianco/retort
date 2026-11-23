defmodule Books.Store do
  use GenServer

  def start_link(path), do: GenServer.start_link(__MODULE__, path, name: __MODULE__)
  def run(operation), do: GenServer.call(__MODULE__, operation)

  @impl true
  def init(path) do
    with {:ok, table} <- :dets.open_file(:book_collection, file: String.to_charlist(path)) do
      :dets.insert_new(table, {:sequence, 0})
      {:ok, table}
    end
  end

  @impl true
  def handle_call(operation, _from, table), do: {:reply, execute(operation, table), table}

  defp execute({:list, author}, table) do
    :dets.foldl(
      fn
        {id, book}, acc when is_integer(id) ->
          if is_nil(author) or book["author"] == author, do: [book | acc], else: acc

        _, acc ->
          acc
      end,
      [],
      table
    )
    |> Enum.sort_by(& &1["id"])
  end

  defp execute({:create, fields}, table) do
    id = :dets.update_counter(table, :sequence, 1)
    save(table, id, fields)
  end

  defp execute({operation, id}, table) do
    case :dets.lookup(table, id) do
      [] ->
        :missing

      [{^id, book}] ->
        case operation do
          :get ->
            book

          :delete ->
            :ok = :dets.delete(table, id)
            :ok = :dets.sync(table)

          {:replace, fields} ->
            save(table, id, fields)
        end
    end
  end

  defp save(table, id, fields) do
    book = Map.put(fields, "id", id)
    :ok = :dets.insert(table, {id, book})
    :ok = :dets.sync(table)
    book
  end
end
