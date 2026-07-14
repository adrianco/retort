ExUnit.start()
# The data store is loaded once by the application supervisor before tests run.
Application.ensure_all_started(:brazilian_soccer)
