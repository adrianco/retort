package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func newTestServer(t *testing.T) (*Server, *sql.DB) {
	t.Helper()
	db, err := sql.Open("sqlite3", "file:"+t.Name()+"?mode=memory&cache=shared")
	if err != nil {
		t.Fatalf("open test database: %v", err)
	}
	db.SetMaxOpenConns(1)
	server, err := NewServer(db)
	if err != nil {
		db.Close()
		t.Fatalf("create server: %v", err)
	}
	return server, db
}

func request(t *testing.T, server http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	response := httptest.NewRecorder()
	server.ServeHTTP(response, req)
	return response
}

func decodeResponse[T any](t *testing.T, response *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.NewDecoder(response.Body).Decode(&value); err != nil {
		t.Fatalf("decode response: %v; body=%q", err, response.Body.String())
	}
	return value
}

func TestCreateAndGetBook(t *testing.T) {
	server, db := newTestServer(t)
	defer db.Close()

	createdResponse := request(t, server, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if createdResponse.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d; body=%s", createdResponse.Code, http.StatusCreated, createdResponse.Body)
	}
	created := decodeResponse[Book](t, createdResponse)
	if created.ID == 0 || created.Title != "Dune" || created.Author != "Frank Herbert" {
		t.Fatalf("unexpected created book: %#v", created)
	}

	fetchedResponse := request(t, server, http.MethodGet, "/books/1", "")
	if fetchedResponse.Code != http.StatusOK {
		t.Fatalf("get status = %d, want %d", fetchedResponse.Code, http.StatusOK)
	}
	fetched := decodeResponse[Book](t, fetchedResponse)
	if fetched != created {
		t.Fatalf("fetched = %#v, want %#v", fetched, created)
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	server, db := newTestServer(t)
	defer db.Close()

	request(t, server, http.MethodPost, "/books", `{"title":"A Wizard of Earthsea","author":"Ursula Le Guin","year":1968,"isbn":"1"}`)
	request(t, server, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"2"}`)
	request(t, server, http.MethodPost, "/books", `{"title":"The Dispossessed","author":"Ursula Le Guin","year":1974,"isbn":"3"}`)

	response := request(t, server, http.MethodGet, "/books?author=Ursula%20Le%20Guin", "")
	if response.Code != http.StatusOK {
		t.Fatalf("list status = %d, want %d", response.Code, http.StatusOK)
	}
	books := decodeResponse[[]Book](t, response)
	if len(books) != 2 || books[0].Title != "A Wizard of Earthsea" || books[1].Title != "The Dispossessed" {
		t.Fatalf("filtered books = %#v", books)
	}
}

func TestUpdateThenDeleteBook(t *testing.T) {
	server, db := newTestServer(t)
	defer db.Close()

	request(t, server, http.MethodPost, "/books", `{"title":"Old title","author":"Writer","year":2000,"isbn":"old"}`)
	updated := request(t, server, http.MethodPut, "/books/1", `{"title":"New title","author":"New Writer","year":2001,"isbn":"new"}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status = %d, want %d; body=%s", updated.Code, http.StatusOK, updated.Body)
	}
	book := decodeResponse[Book](t, updated)
	if book.Title != "New title" || book.Year != 2001 {
		t.Fatalf("updated book = %#v", book)
	}

	deleted := request(t, server, http.MethodDelete, "/books/1", "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want %d", deleted.Code, http.StatusNoContent)
	}
	notFound := request(t, server, http.MethodGet, "/books/1", "")
	if notFound.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want %d", notFound.Code, http.StatusNotFound)
	}
}

func TestBookValidationAndHealth(t *testing.T) {
	server, db := newTestServer(t)
	defer db.Close()

	invalid := request(t, server, http.MethodPost, "/books", `{"title":"Only title"}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d, want %d", invalid.Code, http.StatusBadRequest)
	}
	errorBody := decodeResponse[map[string]string](t, invalid)
	if errorBody["error"] != "author is required" {
		t.Fatalf("validation error = %q", errorBody["error"])
	}

	health := request(t, server, http.MethodGet, "/health", "")
	if health.Code != http.StatusOK {
		t.Fatalf("health status = %d, want %d", health.Code, http.StatusOK)
	}
	status := decodeResponse[map[string]string](t, health)
	if status["status"] != "ok" {
		t.Fatalf("health response = %#v", status)
	}
}

func TestUnknownJSONFieldIsRejected(t *testing.T) {
	server, db := newTestServer(t)
	defer db.Close()

	response := request(t, server, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","unexpected":true}`)
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusBadRequest)
	}
	if _, err := io.ReadAll(response.Body); err != nil {
		t.Fatalf("read response body: %v", err)
	}
}
