# BookApi.Repo is started automatically as part of the :book_api application.
# Reset the test database to a clean, migrated state, then run each test inside
# a sandboxed transaction.
alias Ecto.Adapters.SQL.Sandbox

_ = BookApi.Repo.__adapter__().storage_up(BookApi.Repo.config())
Ecto.Migrator.run(BookApi.Repo, :up, all: true)

Sandbox.mode(BookApi.Repo, :manual)

ExUnit.start()
