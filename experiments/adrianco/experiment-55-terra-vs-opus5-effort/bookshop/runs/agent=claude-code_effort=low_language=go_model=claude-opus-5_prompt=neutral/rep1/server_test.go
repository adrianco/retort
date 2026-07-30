package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, s *Server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, req)
	return rec
}

func mustCreate(t *testing.T, s *Server, title, author string, year int, isbn string) Book {
	t.Helper()
	rec := do(t, s, http.MethodPost, "/books", map[string]any{
		"title": title, "author": author, "year": year, "isbn": isbn,
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create %q: status = %d, body = %s", title, rec.Code, rec.Body)
	}
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode created book: %v", err)
	}
	return b
}

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)

	created := mustCreate(t, s, "Dune", "Frank Herbert", 1965, "9780441013593")
	if created.ID == 0 {
		t.Fatal("expected server-assigned ID")
	}

	rec := do(t, s, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: status = %d, want 200", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got != created {
		t.Errorf("get returned %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	s := newTestServer(t)

	cases := map[string]map[string]any{
		"missing title":  {"author": "Someone"},
		"blank title":    {"title": "   ", "author": "Someone"},
		"missing author": {"title": "Untitled"},
		"blank author":   {"title": "Untitled", "author": ""},
		"bad year":       {"title": "Untitled", "author": "Someone", "year": 9999},
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			rec := do(t, s, http.MethodPost, "/books", body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400 (body %s)", rec.Code, rec.Body)
			}
			var resp map[string]string
			if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
				t.Fatalf("decode error body: %v", err)
			}
			if resp["error"] == "" {
				t.Error("expected non-empty error message")
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	s := newTestServer(t)
	mustCreate(t, s, "Dune", "Frank Herbert", 1965, "a")
	mustCreate(t, s, "Children of Dune", "Frank Herbert", 1976, "b")
	mustCreate(t, s, "Neuromancer", "William Gibson", 1984, "c")

	all := listBooks(t, s, "/books")
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	filtered := listBooks(t, s, "/books?author=Frank+Herbert")
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered results", b.Author)
		}
	}

	if none := listBooks(t, s, "/books?author=Nobody"); len(none) != 0 {
		t.Errorf("len(none) = %d, want 0", len(none))
	}
}

func TestUpdateAndDelete(t *testing.T) {
	s := newTestServer(t)
	created := mustCreate(t, s, "Nueromancer", "William Gibson", 1984, "c")
	path := "/books/" + itoa(created.ID)

	rec := do(t, s, http.MethodPut, path, map[string]any{
		"title": "Neuromancer", "author": "William Gibson", "year": 1984, "isbn": "9780441569595",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: status = %d, body = %s", rec.Code, rec.Body)
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if updated.Title != "Neuromancer" || updated.ISBN != "9780441569595" || updated.ID != created.ID {
		t.Fatalf("update returned %+v", updated)
	}

	if rec := do(t, s, http.MethodDelete, path, nil); rec.Code != http.StatusNoContent {
		t.Fatalf("delete: status = %d, want 204", rec.Code)
	}
	if rec := do(t, s, http.MethodGet, path, nil); rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: status = %d, want 404", rec.Code)
	}
}

func TestMissingBookReturns404(t *testing.T) {
	s := newTestServer(t)
	body := map[string]any{"title": "X", "author": "Y"}

	for _, tc := range []struct {
		method, path string
		body         any
	}{
		{http.MethodGet, "/books/42", nil},
		{http.MethodPut, "/books/42", body},
		{http.MethodDelete, "/books/42", nil},
	} {
		if rec := do(t, s, tc.method, tc.path, tc.body); rec.Code != http.StatusNotFound {
			t.Errorf("%s %s: status = %d, want 404", tc.method, tc.path, rec.Code)
		}
	}

	if rec := do(t, s, http.MethodGet, "/books/abc", nil); rec.Code != http.StatusBadRequest {
		t.Errorf("non-numeric id: status = %d, want 400", rec.Code)
	}
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("status = %q, want \"ok\"", resp["status"])
	}
}

func listBooks(t *testing.T, s *Server, path string) []Book {
	t.Helper()
	rec := do(t, s, http.MethodGet, path, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list %s: status = %d", path, rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	return books
}

func itoa(id int64) string { return strconv.FormatInt(id, 10) }
