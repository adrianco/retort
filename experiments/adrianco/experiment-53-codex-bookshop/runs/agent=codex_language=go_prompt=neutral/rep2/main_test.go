package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func testServer(t *testing.T) (*Server, http.Handler) {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	s, err := NewServer(db)
	if err != nil {
		t.Fatal(err)
	}
	return s, s.Handler()
}

func request(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr
}

func TestCreateAndGetBook(t *testing.T) {
	_, h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d", created.Code)
	}
	var book Book
	if err := json.NewDecoder(created.Body).Decode(&book); err != nil {
		t.Fatal(err)
	}
	if book.ID != 1 || book.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", book)
	}
	got := request(t, h, http.MethodGet, "/books/1", "")
	if got.Code != http.StatusOK {
		t.Fatalf("get status = %d", got.Code)
	}
}

func TestListFiltersByAuthor(t *testing.T) {
	_, h := testServer(t)
	for _, body := range []string{`{"title":"Dune","author":"Herbert"}`, `{"title":"Foundation","author":"Asimov"}`} {
		if code := request(t, h, http.MethodPost, "/books", body).Code; code != http.StatusCreated {
			t.Fatalf("create status = %d", code)
		}
	}
	rr := request(t, h, http.MethodGet, "/books?author=Herbert", "")
	var books []Book
	if err := json.NewDecoder(rr.Body).Decode(&books); err != nil {
		t.Fatal(err)
	}
	if rr.Code != http.StatusOK || len(books) != 1 || books[0].Author != "Herbert" {
		t.Fatalf("unexpected filtered response: %d %+v", rr.Code, books)
	}
}

func TestValidationUpdateAndDelete(t *testing.T) {
	_, h := testServer(t)
	bad := request(t, h, http.MethodPost, "/books", `{"title":"","author":"Someone"}`)
	if bad.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", bad.Code)
	}
	request(t, h, http.MethodPost, "/books", `{"title":"Old","author":"Author"}`)
	updated := request(t, h, http.MethodPut, "/books/1", `{"title":"New","author":"Author","year":2020}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status = %d", updated.Code)
	}
	deleted := request(t, h, http.MethodDelete, "/books/1", "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", deleted.Code)
	}
	missing := request(t, h, http.MethodGet, "/books/1", "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status = %d", missing.Code)
	}
}
