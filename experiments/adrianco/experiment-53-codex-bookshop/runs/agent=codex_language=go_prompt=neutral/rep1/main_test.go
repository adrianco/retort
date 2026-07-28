package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
)

func testServer(t *testing.T) (*Server, func()) {
	t.Helper()
	store, err := OpenStore("file:test_" + t.Name() + "?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	return &Server{store: store}, func() { store.Close() }
}

func request(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	r := httptest.NewRequest(method, path, &buf)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	s, done := testServer(t)
	defer done()
	w := request(t, s.Handler(), http.MethodPost, "/books", bookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"})
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d", w.Code)
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	w = request(t, s.Handler(), http.MethodGet, "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusOK || !bytes.Contains(w.Body.Bytes(), []byte(`"title":"Dune"`)) {
		t.Fatalf("get response = %d %s", w.Code, w.Body.String())
	}
}

func TestValidationAndAuthorFilter(t *testing.T) {
	s, done := testServer(t)
	defer done()
	w := request(t, s.Handler(), http.MethodPost, "/books", bookInput{Title: "", Author: "Someone"})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", w.Code)
	}
	for _, in := range []bookInput{{Title: "One", Author: "Alice"}, {Title: "Two", Author: "Bob"}} {
		if request(t, s.Handler(), http.MethodPost, "/books", in).Code != 201 {
			t.Fatal("seed failed")
		}
	}
	w = request(t, s.Handler(), http.MethodGet, "/books?author=Alice", nil)
	if w.Code != 200 || bytes.Count(w.Body.Bytes(), []byte(`"id"`)) != 1 {
		t.Fatalf("filter response = %d %s", w.Code, w.Body.String())
	}
}

func TestUpdateDeleteAndHealth(t *testing.T) {
	s, done := testServer(t)
	defer done()
	b, err := s.store.Create(context.Background(), bookInput{Title: "Old", Author: "A"})
	if err != nil {
		t.Fatal(err)
	}
	w := request(t, s.Handler(), http.MethodPut, "/books/"+itoa(b.ID), bookInput{Title: "New", Author: "B"})
	if w.Code != 200 || !bytes.Contains(w.Body.Bytes(), []byte(`"title":"New"`)) {
		t.Fatalf("update response = %d %s", w.Code, w.Body.String())
	}
	w = request(t, s.Handler(), http.MethodDelete, "/books/"+itoa(b.ID), nil)
	if w.Code != 204 {
		t.Fatalf("delete status = %d", w.Code)
	}
	w = request(t, s.Handler(), http.MethodGet, "/health", nil)
	if w.Code != 200 {
		t.Fatalf("health status = %d", w.Code)
	}
	if _, err := s.store.Get(context.Background(), b.ID); err != sql.ErrNoRows {
		t.Fatalf("book still exists: %v", err)
	}
}

func itoa(id int64) string { return fmt.Sprintf("%d", id) }
