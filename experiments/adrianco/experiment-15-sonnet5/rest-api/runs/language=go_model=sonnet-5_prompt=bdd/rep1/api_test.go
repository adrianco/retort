package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "modernc.org/sqlite"
)

// newTestAPI wires up a fresh in-memory database for each test so scenarios
// never share state.
func newTestAPI(t *testing.T) *API {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("failed to open in-memory db: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	store, err := NewStore(db)
	if err != nil {
		t.Fatalf("failed to init store: %v", err)
	}
	return NewAPI(store)
}

func doRequest(api *API, method, path string, body interface{}) *httptest.ResponseRecorder {
	var reader *bytes.Reader
	if body != nil {
		data, _ := json.Marshal(body)
		reader = bytes.NewReader(data)
	} else {
		reader = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, path, reader)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	api.Routes().ServeHTTP(rec, req)
	return rec
}

func decodeBook(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("failed to decode book response: %v (body: %s)", err, rec.Body.String())
	}
	return b
}

func Test_given_server_when_health_endpoint_is_called_then_it_returns_ok(t *testing.T) {
	// Given a running API
	api := newTestAPI(t)

	// When the health endpoint is called
	rec := doRequest(api, http.MethodGet, "/health", nil)

	// Then it responds with 200 OK
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
}

func Test_given_valid_book_when_created_then_it_is_persisted_with_an_id(t *testing.T) {
	// Given a valid book payload
	api := newTestAPI(t)
	newBook := Book{Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937, ISBN: "978-0345339683"}

	// When the book is created via POST /books
	rec := doRequest(api, http.MethodPost, "/books", newBook)

	// Then the response is 201 Created and contains the persisted book with an ID
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected status 201, got %d (body: %s)", rec.Code, rec.Body.String())
	}
	created := decodeBook(t, rec)
	if created.ID == 0 {
		t.Fatalf("expected created book to have a non-zero ID")
	}
	if created.Title != newBook.Title || created.Author != newBook.Author {
		t.Fatalf("expected created book to match input, got %+v", created)
	}
}

func Test_given_missing_title_when_book_is_created_then_it_is_rejected(t *testing.T) {
	// Given a book payload missing the required title field
	api := newTestAPI(t)
	invalidBook := Book{Author: "Anonymous"}

	// When the book is created via POST /books
	rec := doRequest(api, http.MethodPost, "/books", invalidBook)

	// Then the response is 400 Bad Request
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d (body: %s)", rec.Code, rec.Body.String())
	}
}

func Test_given_missing_author_when_book_is_created_then_it_is_rejected(t *testing.T) {
	// Given a book payload missing the required author field
	api := newTestAPI(t)
	invalidBook := Book{Title: "Untitled"}

	// When the book is created via POST /books
	rec := doRequest(api, http.MethodPost, "/books", invalidBook)

	// Then the response is 400 Bad Request
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d (body: %s)", rec.Code, rec.Body.String())
	}
}

func Test_given_existing_book_when_fetched_by_id_then_it_is_returned(t *testing.T) {
	// Given an existing book
	api := newTestAPI(t)
	createRec := doRequest(api, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	created := decodeBook(t, createRec)

	// When the book is fetched by its ID
	rec := doRequest(api, http.MethodGet, "/books/"+itoa(created.ID), nil)

	// Then the same book is returned
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	fetched := decodeBook(t, rec)
	if fetched.ID != created.ID || fetched.Title != created.Title {
		t.Fatalf("expected fetched book to match created book, got %+v", fetched)
	}
}

func Test_given_no_book_with_id_when_fetched_then_not_found_is_returned(t *testing.T) {
	// Given no book exists with a particular ID
	api := newTestAPI(t)

	// When that ID is requested
	rec := doRequest(api, http.MethodGet, "/books/9999", nil)

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404, got %d", rec.Code)
	}
}

func Test_given_books_by_multiple_authors_when_listed_with_author_filter_then_only_matches_are_returned(t *testing.T) {
	// Given books from two different authors
	api := newTestAPI(t)
	doRequest(api, http.MethodPost, "/books", Book{Title: "Foundation", Author: "Isaac Asimov"})
	doRequest(api, http.MethodPost, "/books", Book{Title: "I, Robot", Author: "Isaac Asimov"})
	doRequest(api, http.MethodPost, "/books", Book{Title: "Neuromancer", Author: "William Gibson"})

	// When the list is filtered by one author
	rec := doRequest(api, http.MethodGet, "/books?author=Isaac+Asimov", nil)

	// Then only that author's books are returned
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("failed to decode books list: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2 books by Isaac Asimov, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Isaac Asimov" {
			t.Fatalf("expected only Isaac Asimov books, got author %q", b.Author)
		}
	}
}

func Test_given_existing_book_when_updated_then_new_values_are_persisted(t *testing.T) {
	// Given an existing book
	api := newTestAPI(t)
	createRec := doRequest(api, http.MethodPost, "/books", Book{Title: "Old Title", Author: "Old Author", Year: 2000})
	created := decodeBook(t, createRec)

	// When the book is updated with new values
	updatePayload := Book{Title: "New Title", Author: "New Author", Year: 2020, ISBN: "123"}
	rec := doRequest(api, http.MethodPut, "/books/"+itoa(created.ID), updatePayload)

	// Then the update response reflects the new values
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d (body: %s)", rec.Code, rec.Body.String())
	}
	updated := decodeBook(t, rec)
	if updated.Title != "New Title" || updated.Author != "New Author" || updated.Year != 2020 {
		t.Fatalf("expected updated fields to persist, got %+v", updated)
	}

	// And fetching the book again shows the persisted change
	getRec := doRequest(api, http.MethodGet, "/books/"+itoa(created.ID), nil)
	refetched := decodeBook(t, getRec)
	if refetched.Title != "New Title" {
		t.Fatalf("expected persisted title to be 'New Title', got %q", refetched.Title)
	}
}

func Test_given_no_book_with_id_when_updated_then_not_found_is_returned(t *testing.T) {
	// Given no book exists with a particular ID
	api := newTestAPI(t)

	// When an update is attempted on that ID
	rec := doRequest(api, http.MethodPut, "/books/9999", Book{Title: "X", Author: "Y"})

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404, got %d", rec.Code)
	}
}

func Test_given_existing_book_when_deleted_then_it_can_no_longer_be_fetched(t *testing.T) {
	// Given an existing book
	api := newTestAPI(t)
	createRec := doRequest(api, http.MethodPost, "/books", Book{Title: "Ephemeral", Author: "Someone"})
	created := decodeBook(t, createRec)

	// When the book is deleted
	deleteRec := doRequest(api, http.MethodDelete, "/books/"+itoa(created.ID), nil)

	// Then the delete response is 204 No Content
	if deleteRec.Code != http.StatusNoContent {
		t.Fatalf("expected status 204, got %d", deleteRec.Code)
	}

	// And subsequent fetches return 404 Not Found
	getRec := doRequest(api, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if getRec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404 after deletion, got %d", getRec.Code)
	}
}

func Test_given_no_book_with_id_when_deleted_then_not_found_is_returned(t *testing.T) {
	// Given no book exists with a particular ID
	api := newTestAPI(t)

	// When a delete is attempted on that ID
	rec := doRequest(api, http.MethodDelete, "/books/9999", nil)

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404, got %d", rec.Code)
	}
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
