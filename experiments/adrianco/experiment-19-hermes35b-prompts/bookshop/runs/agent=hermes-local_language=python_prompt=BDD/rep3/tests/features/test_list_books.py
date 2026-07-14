"""BDD step definitions for List Books feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("list_books.feature")


@given("I have added three books to the catalogue")
def _(app_client, scenario_data):
    books = []
    for title, author in [("Book 1", "Author A"), ("Book 2", "Author B"), ("Book 3", "Author A")]:
        resp = app_client.post("/books", json={"title": title, "author": author})
        books.append(resp.get_json())
    scenario_data["books"] = books


@when("I request the list of all books")
def _(app_client, scenario_data):
    scenario_data["response"] = app_client.get("/books")


@then("the response status is 200")
def _(scenario_data):
    assert scenario_data["response"].status_code == 200


@then("the response body is a list of three books")
def _(scenario_data):
    books = scenario_data["response"].get_json()
    assert len(books) == 3


@given("I have added books by multiple authors")
def _(app_client, scenario_data):
    books = []
    for title, author in [("Book 1", "J K Rowling"), ("Book 2", "Author B"), ("Book 3", "J K Rowling")]:
        resp = app_client.post("/books", json={"title": title, "author": author})
        books.append(resp.get_json())
    scenario_data["books"] = books


@when("I request books filtered by author J K Rowling")
def _(app_client, scenario_data):
    scenario_data["response"] = app_client.get("/books?author=J%20K%20Rowling")


@then("only books by J K Rowling are returned")
def _(scenario_data):
    books = scenario_data["response"].get_json()
    assert len(books) >= 1
    for book in books:
        assert book["author"] == "J K Rowling"


@given("the catalogue is empty")
def _():
    pass


@then("the response body is an empty list")
def _(scenario_data):
    books = scenario_data["response"].get_json()
    assert books == []
