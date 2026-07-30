package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(t.TempDir() + "/books.db")
	if err != nil {
		t.Fatalf("NewStore() error = %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("store.Close() error = %v", err)
		}
	})
	return NewHandler(store)
}

func request(t *testing.T, handler http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, req)
	return recorder
}

func decodeBook(t *testing.T, recorder *httptest.ResponseRecorder) Book {
	t.Helper()
	var book Book
	if err := json.NewDecoder(recorder.Body).Decode(&book); err != nil {
		t.Fatalf("decode book response: %v; body=%s", err, recorder.Body.String())
	}
	return book
}

func TestHealth(t *testing.T) {
	handler := newTestHandler(t)
	recorder := request(t, handler, http.MethodGet, "/health", "")

	if recorder.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want %d", recorder.Code, http.StatusOK)
	}
	if got := recorder.Header().Get("Content-Type"); !strings.HasPrefix(got, "application/json") {
		t.Fatalf("Content-Type = %q, want application/json", got)
	}

	var response map[string]string
	if err := json.NewDecoder(recorder.Body).Decode(&response); err != nil {
		t.Fatalf("decode health response: %v", err)
	}
	if response["status"] != "ok" {
		t.Fatalf("health response = %#v, want status ok", response)
	}
}

func TestBookCRUD(t *testing.T) {
	handler := newTestHandler(t)

	createdResponse := request(t, handler, http.MethodPost, "/books", `{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}`)
	if createdResponse.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want %d; body=%s", createdResponse.Code, http.StatusCreated, createdResponse.Body.String())
	}
	created := decodeBook(t, createdResponse)
	if created.ID < 1 || created.Title != "Kindred" || created.Author != "Octavia E. Butler" {
		t.Fatalf("created book = %#v, want assigned ID and submitted fields", created)
	}

	getResponse := request(t, handler, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if getResponse.Code != http.StatusOK {
		t.Fatalf("GET /books/{id} status = %d, want %d", getResponse.Code, http.StatusOK)
	}
	if got := decodeBook(t, getResponse); got != created {
		t.Fatalf("GET /books/{id} = %#v, want %#v", got, created)
	}

	updatedResponse := request(t, handler, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), `{"title":"Kindred (updated)","author":"Octavia E. Butler","year":1980,"isbn":"updated-isbn"}`)
	if updatedResponse.Code != http.StatusOK {
		t.Fatalf("PUT /books/{id} status = %d, want %d; body=%s", updatedResponse.Code, http.StatusOK, updatedResponse.Body.String())
	}
	updated := decodeBook(t, updatedResponse)
	if updated.Title != "Kindred (updated)" || updated.Year != 1980 || updated.ISBN != "updated-isbn" {
		t.Fatalf("updated book = %#v, fields were not replaced", updated)
	}

	deletedResponse := request(t, handler, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if deletedResponse.Code != http.StatusNoContent {
		t.Fatalf("DELETE /books/{id} status = %d, want %d", deletedResponse.Code, http.StatusNoContent)
	}
	if deletedResponse.Body.Len() != 0 {
		t.Fatalf("DELETE /books/{id} body = %q, want empty", deletedResponse.Body.String())
	}

	notFoundResponse := request(t, handler, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if notFoundResponse.Code != http.StatusNotFound {
		t.Fatalf("GET deleted book status = %d, want %d", notFoundResponse.Code, http.StatusNotFound)
	}
}

func TestListBooksCanFilterByAuthor(t *testing.T) {
	handler := newTestHandler(t)

	for _, payload := range []string{
		`{"title":"Parable of the Sower","author":"Octavia Butler","year":1993,"isbn":"1"}`,
		`{"title":"The Left Hand of Darkness","author":"Ursula Le Guin","year":1969,"isbn":"2"}`,
		`{"title":"Dawn","author":"Octavia Butler","year":1987,"isbn":"3"}`,
	} {
		recorder := request(t, handler, http.MethodPost, "/books", payload)
		if recorder.Code != http.StatusCreated {
			t.Fatalf("POST /books status = %d, want %d; body=%s", recorder.Code, http.StatusCreated, recorder.Body.String())
		}
	}

	recorder := request(t, handler, http.MethodGet, "/books?author=Octavia+Butler", "")
	if recorder.Code != http.StatusOK {
		t.Fatalf("GET /books?author= status = %d, want %d", recorder.Code, http.StatusOK)
	}
	var books []Book
	if err := json.NewDecoder(recorder.Body).Decode(&books); err != nil {
		t.Fatalf("decode book list: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("filtered book count = %d, want 2; books=%#v", len(books), books)
	}
	for _, book := range books {
		if book.Author != "Octavia Butler" {
			t.Fatalf("filtered book author = %q, want Octavia Butler", book.Author)
		}
	}
}

func TestBookValidation(t *testing.T) {
	handler := newTestHandler(t)

	for _, payload := range []string{
		`{"title":"","author":"Someone"}`,
		`{"title":"A title","author":"   "}`,
		`not json`,
	} {
		recorder := request(t, handler, http.MethodPost, "/books", payload)
		if recorder.Code != http.StatusBadRequest {
			t.Fatalf("POST /books payload %q status = %d, want %d; body=%s", payload, recorder.Code, http.StatusBadRequest, recorder.Body.String())
		}
		if got := recorder.Header().Get("Content-Type"); !strings.HasPrefix(got, "application/json") {
			t.Fatalf("error Content-Type = %q, want application/json", got)
		}
	}
}
