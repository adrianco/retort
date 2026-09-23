package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
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
	return s
}

func do(t *testing.T, s *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, "GET", "/health", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
}

func TestValidation(t *testing.T) {
	s := newTestServer(t)
	for _, body := range []string{`{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `not json`} {
		if rec := do(t, s, "POST", "/books", body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %s: got %d", body, rec.Code)
		}
	}
}

func TestCRUD(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var b Book
	json.Unmarshal(rec.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 {
		t.Fatalf("bad book %+v", b)
	}

	rec = do(t, s, "GET", "/books/1", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Dune") {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}

	rec = do(t, s, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Messiah") {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}
	if rec := do(t, s, "PUT", "/books/99", `{"title":"X","author":"Y"}`); rec.Code != 404 {
		t.Fatalf("update missing: %d", rec.Code)
	}

	if rec := do(t, s, "DELETE", "/books/1", ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec := do(t, s, "GET", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("get deleted: %d", rec.Code)
	}
	if rec := do(t, s, "DELETE", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("delete again: %d", rec.Code)
	}
	if rec := do(t, s, "GET", "/books/abc", ""); rec.Code != 400 {
		t.Fatalf("bad id: %d", rec.Code)
	}
}

func TestListAuthorFilter(t *testing.T) {
	s := newTestServer(t)
	do(t, s, "POST", "/books", `{"title":"A1","author":"Alice"}`)
	do(t, s, "POST", "/books", `{"title":"B1","author":"Bob"}`)
	do(t, s, "POST", "/books", `{"title":"A2","author":"Alice"}`)

	var all, alice []Book
	json.Unmarshal(do(t, s, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(t, s, "GET", "/books?author=alice", "").Body.Bytes(), &alice)
	if len(all) != 3 || len(alice) != 2 {
		t.Fatalf("all=%d alice=%d", len(all), len(alice))
	}
	rec := do(t, s, "GET", "/books?author=nobody", "")
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list should be [], got %s", rec.Body)
	}
}
