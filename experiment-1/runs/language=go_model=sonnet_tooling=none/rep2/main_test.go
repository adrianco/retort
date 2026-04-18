package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestApp(t *testing.T) *App {
	t.Helper()
	app, err := NewApp(":memory:")
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	t.Cleanup(func() { app.db.Close() })
	return app
}

func TestHealth(t *testing.T) {
	app := newTestApp(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var body map[string]string
	json.NewDecoder(w.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", body["status"])
	}
}

func TestCreateBook(t *testing.T) {
	app := newTestApp(t)

	payload := `{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}
	var b Book
	json.NewDecoder(w.Body).Decode(&b)
	if b.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if b.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title: %q", b.Title)
	}
}

func TestCreateBookValidation(t *testing.T) {
	app := newTestApp(t)

	cases := []struct {
		name    string
		payload string
	}{
		{"missing title", `{"author":"Someone"}`},
		{"missing author", `{"title":"Some Book"}`},
		{"empty title", `{"title":"  ","author":"Someone"}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(tc.payload))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			app.Routes().ServeHTTP(w, req)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("expected 400, got %d", w.Code)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	app := newTestApp(t)
	srv := httptest.NewServer(app.Routes())
	defer srv.Close()

	// seed two books
	for _, payload := range []string{
		`{"title":"Book A","author":"Alice"}`,
		`{"title":"Book B","author":"Bob"}`,
	} {
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload))
		req.Header.Set("Content-Type", "application/json")
		app.Routes().ServeHTTP(httptest.NewRecorder(), req)
	}

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	app.Routes().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var books []Book
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 2 {
		t.Fatalf("expected 2 books, got %d", len(books))
	}
}

func TestListBooksFilterByAuthor(t *testing.T) {
	app := newTestApp(t)
	routes := app.Routes()

	for _, payload := range []string{
		`{"title":"Book A","author":"Alice"}`,
		`{"title":"Book B","author":"Bob"}`,
		`{"title":"Book C","author":"Alice"}`,
	} {
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload))
		req.Header.Set("Content-Type", "application/json")
		routes.ServeHTTP(httptest.NewRecorder(), req)
	}

	req := httptest.NewRequest(http.MethodGet, "/books?author=Alice", nil)
	w := httptest.NewRecorder()
	routes.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var books []Book
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 2 {
		t.Fatalf("expected 2 books for Alice, got %d", len(books))
	}
}

func TestGetBookNotFound(t *testing.T) {
	app := newTestApp(t)
	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()
	app.Routes().ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	app := newTestApp(t)
	routes := app.Routes()

	// create
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{"title":"Old Title","author":"Author"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	routes.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d", w.Code)
	}
	var b Book
	json.NewDecoder(w.Body).Decode(&b)

	// update
	upd := bytes.NewBufferString(`{"title":"New Title","author":"Author","year":2024}`)
	req = httptest.NewRequest(http.MethodPut, "/books/"+itoa(b.ID), upd)
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	routes.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var updated Book
	json.NewDecoder(w.Body).Decode(&updated)
	if updated.Title != "New Title" {
		t.Fatalf("expected updated title, got %q", updated.Title)
	}

	// delete
	req = httptest.NewRequest(http.MethodDelete, "/books/"+itoa(b.ID), nil)
	w = httptest.NewRecorder()
	routes.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", w.Code)
	}

	// confirm gone
	req = httptest.NewRequest(http.MethodGet, "/books/"+itoa(b.ID), nil)
	w = httptest.NewRecorder()
	routes.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("after delete: expected 404, got %d", w.Code)
	}
}

func itoa(n int) string {
	return strconv.Itoa(n)
}
