"""BDD step definitions for Update Book feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("update_book.feature")


@given("I have added a book to the catalogue")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={
        "title": "Original Title", "author": "Test Author", "year": 2020
    })
    data = resp.get_json()
    scenario_data["book_id"] = data["id"]


@given("a book with id 999 does not exist")
def _():
    pass


@when("I update the book title to New Title")
def _(app_client, scenario_data):
    book_id = scenario_data["book_id"]
    resp = app_client.put(f"/books/{book_id}", json={"title": "New Title"})
    scenario_data["response"] = resp


@when("I update the book year to 2024")
def _(app_client, scenario_data):
    book_id = scenario_data["book_id"]
    resp = app_client.put(f"/books/{book_id}", json={"year": 2024})
    scenario_data["response"] = resp


@when("I update the book with id 999")
def _(app_client, scenario_data):
    resp = app_client.put("/books/999", json={"title": "Changed"})
    scenario_data["response"] = resp


@then("the response status is 200")
def _(scenario_data):
    assert scenario_data["response"].status_code == 200


@then("the response body contains the updated title")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["title"] == "New Title"


@then("the response body contains the updated year")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["year"] == 2024


@then("the response status is 404")
def _(scenario_data):
    assert scenario_data["response"].status_code == 404
