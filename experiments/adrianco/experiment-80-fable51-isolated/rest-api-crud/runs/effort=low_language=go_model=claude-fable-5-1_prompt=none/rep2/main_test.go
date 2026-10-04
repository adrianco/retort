package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	srv, err := NewServer(":memory:")
	if err != nil {
		t.Fatalf("NewServer: %v", err)
	}
	t.Cleanup(func() { srv.Close() })
	return srv.Handler()
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	rec := do(t, h, "GET", "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)
	rec := do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201: %s", rec.Code, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", created)
	}

	rec = do(t, h, "GET", "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	var got Book
	json.Unmarshal(rec.Body.Bytes(), &got)
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestHandler(t)
	for _, body := range []string{
		`{"author":"Someone"}`,
		`{"title":"No Author"}`,
		`{"title":"  ","author":"Someone"}`,
		`not json`,
	} {
		if rec := do(t, h, "POST", "/books", body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %q: status = %d, want 400", body, rec.Code)
		}
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestHandler(t)
	do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	do(t, h, "POST", "/books", `{"title":"Emma","author":"Jane Austen"}`)
	do(t, h, "POST", "/books", `{"title":"Persuasion","author":"Jane Austen"}`)

	var books []Book
	rec := do(t, h, "GET", "/books", "")
	json.Unmarshal(rec.Body.Bytes(), &books)
	if rec.Code != http.StatusOK || len(books) != 3 {
		t.Fatalf("list: status %d, %d books, want 200 and 3", rec.Code, len(books))
	}

	books = nil
	rec = do(t, h, "GET", "/books?author=Jane+Austen", "")
	json.Unmarshal(rec.Body.Bytes(), &books)
	if len(books) != 2 {
		t.Fatalf("filtered list: %d books, want 2", len(books))
	}

	rec = do(t, h, "GET", "/books?author=Nobody", "")
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list body = %q, want []", rec.Body.String())
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200", rec.Code)
	}
	var b Book
	json.Unmarshal(do(t, h, "GET", "/books/1", "").Body.Bytes(), &b)
	if b.Title != "Dune Messiah" || b.Year != 1969 {
		t.Fatalf("update not persisted: %+v", b)
	}

	if rec := do(t, h, "PUT", "/books/1", `{"title":"","author":"x"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update status = %d, want 400", rec.Code)
	}
	if rec := do(t, h, "PUT", "/books/99", `{"title":"a","author":"b"}`); rec.Code != http.StatusNotFound {
		t.Errorf("missing update status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert"}`)

	if rec := do(t, h, "DELETE", "/books/1", ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}
	if rec := do(t, h, "GET", "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete = %d, want 404", rec.Code)
	}
	if rec := do(t, h, "DELETE", "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete = %d, want 404", rec.Code)
	}
	if rec := do(t, h, "GET", "/books/abc", ""); rec.Code != http.StatusBadRequest {
		t.Errorf("bad id = %d, want 400", rec.Code)
	}
}
