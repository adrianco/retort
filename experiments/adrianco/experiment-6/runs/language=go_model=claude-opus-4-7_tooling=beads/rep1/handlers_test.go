package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	store, err := NewStore(db)
	if err != nil {
		t.Fatalf("init store: %v", err)
	}
	return NewServer(store)
}

func do(t *testing.T, srv *Server, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", w.Code, w.Body.String())
	}
	var got map[string]string
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("unexpected body: %v", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	w := do(t, srv, http.MethodPost, "/books",
		`{"title":"Go","author":"Donovan","year":2015,"isbn":"9780134190440"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create status=%d body=%s", w.Code, w.Body.String())
	}
	var created Book
	if err := json.NewDecoder(w.Body).Decode(&created); err != nil {
		t.Fatalf("decode create: %v", err)
	}
	if created.ID == 0 || created.Title != "Go" || created.Author != "Donovan" {
		t.Fatalf("unexpected created: %+v", created)
	}

	w = do(t, srv, http.MethodGet, "/books/1", "")
	if w.Code != http.StatusOK {
		t.Fatalf("get status=%d body=%s", w.Code, w.Body.String())
	}
	var got Book
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode get: %v", err)
	}
	if got != created {
		t.Fatalf("got %+v want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"A"}`},
		{"missing author", `{"title":"T"}`},
		{"blank title", `{"title":"   ","author":"A"}`},
		{"bad json", `{not json}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := do(t, srv, http.MethodPost, "/books", tc.body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("want 400, got %d body=%s", w.Code, w.Body.String())
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	bodies := []string{
		`{"title":"A1","author":"alice","year":2020,"isbn":"1"}`,
		`{"title":"A2","author":"alice","year":2021,"isbn":"2"}`,
		`{"title":"B1","author":"bob","year":2019,"isbn":"3"}`,
	}
	for _, b := range bodies {
		if w := do(t, srv, http.MethodPost, "/books", b); w.Code != http.StatusCreated {
			t.Fatalf("seed failed: %s", w.Body.String())
		}
	}

	w := do(t, srv, http.MethodGet, "/books", "")
	if w.Code != http.StatusOK {
		t.Fatalf("list status=%d", w.Code)
	}
	var all []Book
	if err := json.NewDecoder(w.Body).Decode(&all); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	w = do(t, srv, http.MethodGet, "/books?author=alice", "")
	if w.Code != http.StatusOK {
		t.Fatalf("filter status=%d", w.Code)
	}
	var alice []Book
	if err := json.NewDecoder(w.Body).Decode(&alice); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("expected 2 alice books, got %d: %+v", len(alice), alice)
	}
	for _, b := range alice {
		if b.Author != "alice" {
			t.Fatalf("unexpected author in filtered list: %s", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	if w := do(t, srv, http.MethodPost, "/books", `{"title":"old","author":"x"}`); w.Code != http.StatusCreated {
		t.Fatalf("seed: %s", w.Body.String())
	}

	w := do(t, srv, http.MethodPut, "/books/1",
		`{"title":"new","author":"y","year":2024,"isbn":"abc"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update status=%d body=%s", w.Code, w.Body.String())
	}
	var got Book
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	want := Book{ID: 1, Title: "new", Author: "y", Year: 2024, ISBN: "abc"}
	if got != want {
		t.Fatalf("got %+v want %+v", got, want)
	}

	w = do(t, srv, http.MethodPut, "/books/999", `{"title":"x","author":"y"}`)
	if w.Code != http.StatusNotFound {
		t.Fatalf("update missing: status=%d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	if w := do(t, srv, http.MethodPost, "/books", `{"title":"t","author":"a"}`); w.Code != http.StatusCreated {
		t.Fatalf("seed: %s", w.Body.String())
	}

	w := do(t, srv, http.MethodDelete, "/books/1", "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status=%d body=%s", w.Code, w.Body.String())
	}

	w = do(t, srv, http.MethodGet, "/books/1", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", w.Code)
	}

	w = do(t, srv, http.MethodDelete, "/books/1", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 on second delete, got %d", w.Code)
	}
}

func TestGetMissingBook(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodGet, "/books/42", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("status=%d", w.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)
	w := do(t, srv, http.MethodPatch, "/books", "")
	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status=%d", w.Code)
	}
}

func TestCreateBookRoundtripBody(t *testing.T) {
	srv := newTestServer(t)
	body := `{"title":"Test","author":"Author","year":2000,"isbn":"x"}`
	w := do(t, srv, http.MethodPost, "/books", body)
	if w.Code != http.StatusCreated {
		t.Fatalf("status=%d", w.Code)
	}
	if !bytes.Contains(w.Body.Bytes(), []byte(`"id":1`)) {
		t.Fatalf("expected id=1 in response: %s", w.Body.String())
	}
}
