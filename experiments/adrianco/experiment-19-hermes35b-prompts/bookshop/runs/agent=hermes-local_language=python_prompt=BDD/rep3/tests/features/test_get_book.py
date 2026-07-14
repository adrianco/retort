"""BDD step definitions for Get Book feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("get_book.feature")


@given("I have added a book to the catalogue")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={
        "title": "Test Book", "author": "Test Author", "year": 2020
    })
    data = resp.get_json()
    scenario_data["book_id"] = data["id"]


@when("I get the book by its id")
def _(app_client, scenario_data):
    book_id = scenario_data["book_id"]
    scenario_data["response"] = app_client.get(f"/books/{book_id}")


@when("I get a book with id 999")
def _(app_client, scenario_data):
    scenario_data["response"] = app_client.get("/books/999")


@then("the response status is 200")
def _(scenario_data):
    assert scenario_data["response"].status_code == 200


@then("the response body contains the book data")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["id"] is not None
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"


@then("the response status is 404")
def _(scenario_data):
    assert scenario_data["response"].status_code == 404
