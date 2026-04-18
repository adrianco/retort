package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	w := do(t, s.Routes(), "GET", "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()

	body := `{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}`
	w := do(t, h, "POST", "/books", body)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected created: %+v", created)
	}

	w = do(t, h, "GET", "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got.Author != "Donovan" {
		t.Fatalf("unexpected author: %s", got.Author)
	}
}

func TestCreateValidation(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()
	w := do(t, h, "POST", "/books", `{"title":"","author":"X"}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
	w = do(t, h, "POST", "/books", `{"title":"T","author":""}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestListFilterAndUpdateAndDelete(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()

	mk := func(title, author string) Book {
		b, _ := json.Marshal(map[string]any{"title": title, "author": author, "year": 2000, "isbn": "x"})
		w := do(t, h, "POST", "/books", string(b))
		if w.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", w.Code, w.Body.String())
		}
		var out Book
		json.Unmarshal(w.Body.Bytes(), &out)
		return out
	}
	a := mk("A", "Alice")
	_ = mk("B", "Bob")
	_ = mk("C", "Alice")

	w := do(t, h, "GET", "/books?author=Alice", "")
	if w.Code != http.StatusOK {
		t.Fatalf("list: %d", w.Code)
	}
	var list []Book
	json.Unmarshal(w.Body.Bytes(), &list)
	if len(list) != 2 {
		t.Fatalf("expected 2 Alice books, got %d", len(list))
	}

	// Update
	upd := bytes.NewBufferString(`{"title":"A2","author":"Alice","year":2001,"isbn":"y"}`)
	r := httptest.NewRequest("PUT", "/books/"+itoa(a.ID), upd)
	r.Header.Set("Content-Type", "application/json")
	rw := httptest.NewRecorder()
	h.ServeHTTP(rw, r)
	if rw.Code != http.StatusOK {
		t.Fatalf("update: %d %s", rw.Code, rw.Body.String())
	}

	// Delete
	w = do(t, h, "DELETE", "/books/"+itoa(a.ID), "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete: %d", w.Code)
	}
	w = do(t, h, "GET", "/books/"+itoa(a.ID), "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", w.Code)
	}
}

func itoa(i int64) string {
	return strings.TrimSpace(jsonNum(i))
}

func jsonNum(i int64) string {
	b, _ := json.Marshal(i)
	return string(b)
}
