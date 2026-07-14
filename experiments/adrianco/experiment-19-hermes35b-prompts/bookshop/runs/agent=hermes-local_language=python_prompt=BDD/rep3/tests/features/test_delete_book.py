"""BDD step definitions for Delete Book feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("delete_book.feature")


@given("I have added a book to the catalogue")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={
        "title": "Test Book", "author": "Test Author", "year": 2020
    })
    data = resp.get_json()
    scenario_data["book_id"] = data["id"]


@given("a book with id 999 does not exist")
def _():
    pass


@when("I delete the book by its id")
def _(app_client, scenario_data):
    book_id = scenario_data["book_id"]
    scenario_data["response"] = app_client.delete(f"/books/{book_id}")


@when("I delete the book with id 999")
def _(app_client, scenario_data):
    scenario_data["response"] = app_client.delete("/books/999")


@when("I delete the book and list all books")
def _(app_client, scenario_data):
    book_id = scenario_data["book_id"]
    app_client.delete(f"/books/{book_id}")
    scenario_data["response"] = app_client.get("/books")


@then("the response status is 200")
def _(scenario_data):
    assert scenario_data["response"].status_code == 200


@then("the book is no longer retrievable")
def _(scenario_data, app_client):
    book_id = scenario_data["book_id"]
    resp = app_client.get(f"/books/{book_id}")
    assert resp.status_code == 404


@then("the response status is 404")
def _(scenario_data):
    assert scenario_data["response"].status_code == 404


@then("the deleted book is not in the list")
def _(scenario_data):
    books = scenario_data["response"].get_json()
    book_ids = [b["id"] for b in books]
    assert scenario_data["book_id"] not in book_ids
