package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *server {
	t.Helper()
	dsn := filepath.Join(t.TempDir(), "test.db")
	st, err := openStore(dsn)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { _ = st.Close() })
	return newServer(st)
}

func do(t *testing.T, srv *server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		r = httptest.NewRequest(method, target, bytes.NewReader(buf))
		r.Header.Set("Content-Type", "application/json")
	} else {
		r = httptest.NewRequest(method, target, nil)
	}
	w := httptest.NewRecorder()
	srv.routes().ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "GET", "/health", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), `"status":"ok"`) {
		t.Fatalf("unexpected body: %s", w.Body.String())
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "POST", "/books", map[string]any{
		"title": "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d body=%s", w.Code, w.Body.String())
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero id, got %+v", created)
	}

	w = do(t, srv, "GET", "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusOK {
		t.Fatalf("get status = %d body=%s", w.Code, w.Body.String())
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got != created {
		t.Fatalf("got %+v want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "POST", "/books", map[string]any{"year": 2020})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400, body=%s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "title is required") ||
		!strings.Contains(w.Body.String(), "author is required") {
		t.Fatalf("missing validation messages: %s", w.Body.String())
	}
}

func TestListFilterByAuthor(t *testing.T) {
	srv := newTestServer(t)
	books := []map[string]any{
		{"title": "A", "author": "Ada", "year": 2001, "isbn": "1"},
		{"title": "B", "author": "Bob", "year": 2002, "isbn": "2"},
		{"title": "C", "author": "Ada", "year": 2003, "isbn": "3"},
	}
	for _, b := range books {
		w := do(t, srv, "POST", "/books", b)
		if w.Code != http.StatusCreated {
			t.Fatalf("seed failed: %s", w.Body.String())
		}
	}

	w := do(t, srv, "GET", "/books?author=Ada", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list status = %d", w.Code)
	}
	var got []Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("got %d books, want 2: %+v", len(got), got)
	}
	for _, b := range got {
		if b.Author != "Ada" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "POST", "/books", map[string]any{
		"title": "Old", "author": "Author", "year": 1999, "isbn": "x",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}
	var created Book
	_ = json.Unmarshal(w.Body.Bytes(), &created)

	w = do(t, srv, "PUT", "/books/"+itoa(created.ID), map[string]any{
		"title": "New", "author": "Author", "year": 2020, "isbn": "y",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("update status = %d body=%s", w.Code, w.Body.String())
	}
	var updated Book
	_ = json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "New" || updated.Year != 2020 || updated.ISBN != "y" {
		t.Fatalf("update did not take effect: %+v", updated)
	}

	w = do(t, srv, "DELETE", "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d body=%s", w.Code, w.Body.String())
	}

	w = do(t, srv, "GET", "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", w.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, "GET", "/books/9999", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
}

func itoa(i int64) string {
	return strconv.FormatInt(i, 10)
}
