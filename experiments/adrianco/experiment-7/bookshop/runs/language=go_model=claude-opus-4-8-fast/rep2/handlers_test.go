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

func do(t *testing.T, srv *Server, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, target, nil)
	} else {
		r = httptest.NewRequest(method, target, strings.NewReader(body))
	}
	w := httptest.NewRecorder()
	srv.Routes().ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(w.Body.String(), "ok") {
		t.Fatalf("unexpected body: %s", w.Body.String())
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)

	w := do(t, srv, http.MethodPost, "/books",
		`{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"978-1617291784"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d (%s)", w.Code, w.Body.String())
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}
	if created.Title != "Go in Action" {
		t.Fatalf("unexpected title: %q", created.Title)
	}

	w = do(t, srv, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", w.Code)
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got != created {
		t.Fatalf("get mismatch: %+v vs %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodPost, "/books", `{"year":2020}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "title is required") || !strings.Contains(body, "author is required") {
		t.Fatalf("expected validation errors, got: %s", body)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	do(t, srv, http.MethodPost, "/books", `{"title":"A","author":"Alice"}`)
	do(t, srv, http.MethodPost, "/books", `{"title":"B","author":"Bob"}`)
	do(t, srv, http.MethodPost, "/books", `{"title":"C","author":"Alice"}`)

	w := do(t, srv, http.MethodGet, "/books?author=Alice", "")
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2 books by Alice, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author in filtered list: %q", b.Author)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)

	w := do(t, srv, http.MethodPost, "/books", `{"title":"Old","author":"Author"}`)
	var created Book
	_ = json.Unmarshal(w.Body.Bytes(), &created)
	id := itoa(created.ID)

	w = do(t, srv, http.MethodPut, "/books/"+id,
		`{"title":"New","author":"Author","year":2021,"isbn":"x"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d (%s)", w.Code, w.Body.String())
	}
	var updated Book
	_ = json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "New" || updated.Year != 2021 {
		t.Fatalf("update did not apply: %+v", updated)
	}

	w = do(t, srv, http.MethodDelete, "/books/"+id, "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", w.Code)
	}

	w = do(t, srv, http.MethodGet, "/books/"+id, "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", w.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/books/9999", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

// itoa converts an int64 to a string without importing strconv in every test.
func itoa(n int64) string {
	var buf bytes.Buffer
	if n == 0 {
		return "0"
	}
	digits := []byte{}
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	buf.Write(digits)
	return buf.String()
}
