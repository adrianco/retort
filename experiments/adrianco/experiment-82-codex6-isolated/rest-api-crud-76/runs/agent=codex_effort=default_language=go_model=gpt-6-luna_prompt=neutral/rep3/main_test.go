package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func testServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	s, err := NewServer(db)
	if err != nil {
		t.Fatal(err)
	}
	return s.Routes()
}

func request(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestCreateAndGetBook(t *testing.T) {
	h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status=%d body=%s", created.Code, created.Body)
	}
	var book Book
	if err := json.Unmarshal(created.Body.Bytes(), &book); err != nil {
		t.Fatal(err)
	}
	if book.ID == 0 {
		t.Fatal("expected assigned ID")
	}
	got := request(t, h, http.MethodGet, "/books/1", "")
	if got.Code != http.StatusOK {
		t.Fatalf("get status=%d", got.Code)
	}
}

func TestValidationAndAuthorFilter(t *testing.T) {
	h := testServer(t)
	bad := request(t, h, http.MethodPost, "/books", `{"title":"","author":"Someone"}`)
	if bad.Code != http.StatusBadRequest {
		t.Fatalf("validation status=%d", bad.Code)
	}
	for _, body := range []string{`{"title":"One","author":"A"}`, `{"title":"Two","author":"B"}`} {
		if r := request(t, h, http.MethodPost, "/books", body); r.Code != http.StatusCreated {
			t.Fatal(r.Body)
		}
	}
	filtered := request(t, h, http.MethodGet, "/books?author=A", "")
	if filtered.Code != http.StatusOK {
		t.Fatal(filtered.Code)
	}
	var books []Book
	if err := json.Unmarshal(filtered.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 1 || books[0].Author != "A" {
		t.Fatalf("unexpected filtered books: %#v", books)
	}
}

func TestUpdateDeleteAndHealth(t *testing.T) {
	h := testServer(t)
	request(t, h, http.MethodPost, "/books", `{"title":"Old","author":"Writer"}`)
	updated := request(t, h, http.MethodPut, "/books/1", `{"title":"New","author":"Writer","year":2024}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status=%d", updated.Code)
	}
	deleted := request(t, h, http.MethodDelete, "/books/1", "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status=%d", deleted.Code)
	}
	missing := request(t, h, http.MethodGet, "/books/1", "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status=%d", missing.Code)
	}
	health := request(t, h, http.MethodGet, "/health", "")
	if health.Code != http.StatusOK {
		t.Fatalf("health status=%d", health.Code)
	}
}
