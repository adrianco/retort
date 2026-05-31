package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore("file::memory:?cache=shared&mode=memory&_pragma=foreign_keys(1)")
	if err != nil {
		// Fallback: use a temp file DB if in-memory DSN options aren't honored.
		store, err = OpenStore(t.TempDir() + "/test.db")
		if err != nil {
			t.Fatalf("open store: %v", err)
		}
	}
	t.Cleanup(func() { _ = store.Close() })
	return NewServer(store)
}

func doRequest(t *testing.T, srv *Server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reqBody *bytes.Buffer
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		reqBody = bytes.NewBuffer(data)
	} else {
		reqBody = &bytes.Buffer{}
	}
	req := httptest.NewRequest(method, path, reqBody)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	srv.Routes().ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, "GET", "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("expected status=ok, got %q", resp["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	book := Book{Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440"}
	rec := doRequest(t, srv, "POST", "/books", book)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d body=%s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode create: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero ID after create")
	}
	if created.Title != book.Title || created.Author != book.Author {
		t.Fatalf("created mismatch: %+v", created)
	}

	rec = doRequest(t, srv, "GET", "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode get: %v", err)
	}
	if got != created {
		t.Fatalf("get mismatch: %+v vs %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, "POST", "/books", Book{Author: "Someone"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing title: expected 400, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "title") {
		t.Fatalf("expected title error message, got %s", rec.Body.String())
	}

	rec = doRequest(t, srv, "POST", "/books", Book{Title: "A Title"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing author: expected 400, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "author") {
		t.Fatalf("expected author error message, got %s", rec.Body.String())
	}
}

func TestListAndFilterByAuthor(t *testing.T) {
	srv := newTestServer(t)

	books := []Book{
		{Title: "Book A", Author: "Alice", Year: 2020},
		{Title: "Book B", Author: "Bob", Year: 2021},
		{Title: "Book C", Author: "Alice", Year: 2022},
	}
	for _, b := range books {
		rec := doRequest(t, srv, "POST", "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("seed create: %d %s", rec.Code, rec.Body.String())
		}
	}

	rec := doRequest(t, srv, "GET", "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: expected 200, got %d", rec.Code)
	}
	var all []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	rec = doRequest(t, srv, "GET", "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("filter: expected 200, got %d", rec.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("decode filter: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books by Alice, got %d", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("filter returned wrong author: %q", b.Author)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, "POST", "/books", Book{Title: "Old", Author: "Author"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d", rec.Code)
	}
	var created Book
	_ = json.Unmarshal(rec.Body.Bytes(), &created)

	updated := Book{Title: "New Title", Author: "New Author", Year: 2024, ISBN: "abc"}
	rec = doRequest(t, srv, "PUT", "/books/"+strconv.FormatInt(created.ID, 10), updated)
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d body=%s", rec.Code, rec.Body.String())
	}
	var got Book
	_ = json.Unmarshal(rec.Body.Bytes(), &got)
	if got.Title != "New Title" || got.Year != 2024 {
		t.Fatalf("update mismatch: %+v", got)
	}

	rec = doRequest(t, srv, "DELETE", "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	rec = doRequest(t, srv, "GET", "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: expected 404, got %d", rec.Code)
	}

	rec = doRequest(t, srv, "DELETE", "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete missing: expected 404, got %d", rec.Code)
	}
}
