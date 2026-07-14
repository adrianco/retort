package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

// newTestServer spins up a Server backed by a fresh in-memory database.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

// do performs a request against the server and returns the recorder.
func do(t *testing.T, srv *Server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader *bytes.Reader
	if body != nil {
		raw, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("failed to marshal body: %v", err)
		}
		reader = bytes.NewReader(raw)
	} else {
		reader = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, target, reader)
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("failed to decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

var validBook = Book{Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "978-0134190440"}

func Test_given_running_server_when_health_checked_then_status_is_ok(t *testing.T) {
	// Given a running server
	srv := newTestServer(t)

	// When the health endpoint is queried
	rec := do(t, srv, http.MethodGet, "/health", nil)

	// Then it responds 200 with an ok status
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	got := decode[map[string]string](t, rec)
	if got["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", got["status"])
	}
}

func Test_given_valid_book_when_created_then_status_is_201_with_assigned_id(t *testing.T) {
	// Given a valid book
	srv := newTestServer(t)

	// When it is posted to /books
	rec := do(t, srv, http.MethodPost, "/books", validBook)

	// Then the response is 201 Created with a generated ID
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d (%s)", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	if got.ID == 0 {
		t.Fatalf("expected a non-zero ID, got %d", got.ID)
	}
	if got.Title != validBook.Title {
		t.Fatalf("expected title %q, got %q", validBook.Title, got.Title)
	}
}

func Test_given_book_without_title_when_created_then_status_is_400(t *testing.T) {
	// Given a book missing its title
	srv := newTestServer(t)
	bad := Book{Author: "Someone", Year: 2020}

	// When it is posted to /books
	rec := do(t, srv, http.MethodPost, "/books", bad)

	// Then the request is rejected with 400 Bad Request
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "title is required") {
		t.Fatalf("expected title validation error, got %q", rec.Body.String())
	}
}

func Test_given_book_without_author_when_created_then_status_is_400(t *testing.T) {
	// Given a book missing its author
	srv := newTestServer(t)
	bad := Book{Title: "Untitled", Year: 2020}

	// When it is posted to /books
	rec := do(t, srv, http.MethodPost, "/books", bad)

	// Then the request is rejected with 400 Bad Request
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "author is required") {
		t.Fatalf("expected author validation error, got %q", rec.Body.String())
	}
}

func Test_given_existing_book_when_fetched_by_id_then_it_is_returned(t *testing.T) {
	// Given an existing book
	srv := newTestServer(t)
	created := decode[Book](t, do(t, srv, http.MethodPost, "/books", validBook))

	// When it is fetched by its ID
	rec := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)

	// Then the matching book is returned with 200 OK
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	got := decode[Book](t, rec)
	if got.ID != created.ID {
		t.Fatalf("expected ID %d, got %d", created.ID, got.ID)
	}
}

func Test_given_no_such_book_when_fetched_by_id_then_status_is_404(t *testing.T) {
	// Given an empty collection
	srv := newTestServer(t)

	// When a non-existent ID is fetched
	rec := do(t, srv, http.MethodGet, "/books/999", nil)

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func Test_given_books_by_different_authors_when_listed_with_author_filter_then_only_matches_returned(t *testing.T) {
	// Given two books by different authors
	srv := newTestServer(t)
	do(t, srv, http.MethodPost, "/books", Book{Title: "A", Author: "Alice", Year: 2001})
	do(t, srv, http.MethodPost, "/books", Book{Title: "B", Author: "Bob", Year: 2002})

	// When the list is filtered by author=Alice
	rec := do(t, srv, http.MethodGet, "/books?author=Alice", nil)

	// Then only Alice's book is returned
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	got := decode[[]Book](t, rec)
	if len(got) != 1 || got[0].Author != "Alice" {
		t.Fatalf("expected exactly one book by Alice, got %+v", got)
	}
}

func Test_given_existing_book_when_updated_then_changes_are_persisted(t *testing.T) {
	// Given an existing book
	srv := newTestServer(t)
	created := decode[Book](t, do(t, srv, http.MethodPost, "/books", validBook))

	// When it is updated with a new title
	updated := created
	updated.Title = "Revised Edition"
	rec := do(t, srv, http.MethodPut, "/books/"+itoa(created.ID), updated)

	// Then the response reflects the change and it is persisted
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d (%s)", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	if got.Title != "Revised Edition" {
		t.Fatalf("expected updated title, got %q", got.Title)
	}
	refetched := decode[Book](t, do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil))
	if refetched.Title != "Revised Edition" {
		t.Fatalf("expected persisted title, got %q", refetched.Title)
	}
}

func Test_given_no_such_book_when_updated_then_status_is_404(t *testing.T) {
	// Given an empty collection
	srv := newTestServer(t)

	// When a non-existent book is updated
	rec := do(t, srv, http.MethodPut, "/books/999", validBook)

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func Test_given_existing_book_when_deleted_then_it_is_gone(t *testing.T) {
	// Given an existing book
	srv := newTestServer(t)
	created := decode[Book](t, do(t, srv, http.MethodPost, "/books", validBook))

	// When it is deleted
	rec := do(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)

	// Then the response is 204 and the book can no longer be fetched
	if rec.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", rec.Code)
	}
	after := do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if after.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", after.Code)
	}
}

func Test_given_no_such_book_when_deleted_then_status_is_404(t *testing.T) {
	// Given an empty collection
	srv := newTestServer(t)

	// When a non-existent book is deleted
	rec := do(t, srv, http.MethodDelete, "/books/999", nil)

	// Then the response is 404 Not Found
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
