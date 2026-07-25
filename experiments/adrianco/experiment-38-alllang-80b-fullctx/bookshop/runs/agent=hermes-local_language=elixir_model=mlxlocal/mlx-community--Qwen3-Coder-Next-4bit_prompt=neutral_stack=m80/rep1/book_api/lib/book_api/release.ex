defmodule BookApi.Release do
  @moduledoc """
  Used for running migrations and seeding the database.
  """
  @app :book_api

  def migrate do
    load_app()

    for repo <- repos() do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, &Ecto.Migrator.run(&1, :up, all: true))
    end
  end

  def seed do
    load_app()

    for repo <- repos() do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, &run_seeds(&1))
    end
  end

  defp run_seeds(repo) do
    {:ok, _} = Application.ensure_all_started(@app)
    seed_path = Path.join([priv_path_for(repo), "repo", "seeds.exs"])
    if File.exists?(seed_path) do
      Code.require_file(seed_path)
    end
    :ok
  end

  defp priv_path_for(repo) do
    app = Keyword.get(repo.config, :otp_app, @app)
    priv_dir = Application.get_env(app, :priv, "priv")
    Path.join([priv_dir, Atom.to_string(repo)])
  end

  defp repos do
    Application.fetch_env!(:book_api, :ecto_repos)
  end

  defp load_app do
    {:ok, _} = Application.ensure_all_started(@app)
  end
end
