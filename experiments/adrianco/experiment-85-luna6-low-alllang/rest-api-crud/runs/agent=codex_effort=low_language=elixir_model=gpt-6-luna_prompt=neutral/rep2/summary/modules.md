# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/book_api/application.ex | OTP application; starts Store + Server under a supervisor | `BookApi.Application.start/2` |
| lib/book_api/server.ex | Hand-rolled HTTP/1.1 server over raw `:gen_tcp`; parses request, routes, sends response | `BookApi.Server.start_link/1` |
| lib/book_api/router.ex | Request dispatch and input validation for all routes | `BookApi.Router.dispatch/4` |
| lib/book_api/store.ex | GenServer persistence layer; shells out to the `sqlite3` CLI | `BookApi.Store.{create,list,get,update,delete}` |
| lib/book_api/json.ex | Dependency-free JSON encoder/decoder | `BookApi.JSON.{encode,decode}` |
| mix.exs | Mix project; zero Hex deps | `BookApi.MixProject` |
| test/book_api_test.exs | Integration tests driving `Router.dispatch/4` | 4 test blocks |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start/0` |
