package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	ts := httptest.NewServer(NewServer(store))
	t.Cleanup(func() {
		ts.Close()
		store.Close()
	})
	return ts
}

func do(t *testing.T, ts *httptest.Server, method, path string, body any) (*http.Response, []byte) {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if s, ok := body.(string); ok {
			buf.WriteString(s)
		} else if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req, err := http.NewRequest(method, ts.URL+path, &buf)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := ts.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var out bytes.Buffer
	out.ReadFrom(resp.Body)
	return resp, out.Bytes()
}

func expectStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("status = %d, want %d; body: %s", resp.StatusCode, want, body)
	}
}

func createBook(t *testing.T, ts *httptest.Server, in bookInput) Book {
	t.Helper()
	resp, body := do(t, ts, http.MethodPost, "/books", in)
	expectStatus(t, resp, body, http.StatusCreated)
	var b Book
	if err := json.Unmarshal(body, &b); err != nil {
		t.Fatal(err)
	}
	return b
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodGet, "/health", nil)
	expectStatus(t, resp, body, http.StatusOK)
	var got map[string]string
	json.Unmarshal(body, &got)
	if got["status"] != "ok" {
		t.Fatalf("health body = %s", body)
	}
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Fatalf("content-type = %q", ct)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	ts := newTestServer(t)

	created := createBook(t, ts, bookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"})
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	resp, body := do(t, ts, http.MethodGet, "/books/1", nil)
	expectStatus(t, resp, body, http.StatusOK)
	var got Book
	json.Unmarshal(body, &got)
	if got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	resp, body = do(t, ts, http.MethodPut, "/books/1", bookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	expectStatus(t, resp, body, http.StatusOK)
	resp, body = do(t, ts, http.MethodGet, "/books/1", nil)
	json.Unmarshal(body, &got)
	if got.Title != "Dune Messiah" || got.Year != 1969 {
		t.Fatalf("update not persisted: %+v", got)
	}

	resp, body = do(t, ts, http.MethodDelete, "/books/1", nil)
	expectStatus(t, resp, body, http.StatusNoContent)
	resp, body = do(t, ts, http.MethodGet, "/books/1", nil)
	expectStatus(t, resp, body, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	resp, body := do(t, ts, http.MethodGet, "/books", nil)
	expectStatus(t, resp, body, http.StatusOK)
	if string(bytes.TrimSpace(body)) != "[]" {
		t.Fatalf("empty list should be [], got %s", body)
	}

	createBook(t, ts, bookInput{Title: "Emma", Author: "Jane Austen"})
	createBook(t, ts, bookInput{Title: "Persuasion", Author: "Jane Austen"})
	createBook(t, ts, bookInput{Title: "Ulysses", Author: "James Joyce"})

	var books []Book
	resp, body = do(t, ts, http.MethodGet, "/books", nil)
	json.Unmarshal(body, &books)
	if len(books) != 3 {
		t.Fatalf("want 3 books, got %d", len(books))
	}

	resp, body = do(t, ts, http.MethodGet, "/books?author=jane%20austen", nil)
	expectStatus(t, resp, body, http.StatusOK)
	books = nil
	json.Unmarshal(body, &books)
	if len(books) != 2 {
		t.Fatalf("want 2 Austen books, got %d: %s", len(books), body)
	}
	for _, b := range books {
		if b.Author != "Jane Austen" {
			t.Fatalf("filter returned wrong author: %+v", b)
		}
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)

	cases := []struct {
		name  string
		body  any
		field string
	}{
		{"missing title", bookInput{Author: "A"}, "title"},
		{"missing author", bookInput{Title: "T"}, "author"},
		{"blank title", bookInput{Title: "   ", Author: "A"}, "title"},
		{"negative year", bookInput{Title: "T", Author: "A", Year: -5}, "year"},
		{"bad isbn", bookInput{Title: "T", Author: "A", ISBN: "abc"}, "isbn"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := do(t, ts, http.MethodPost, "/books", tc.body)
			expectStatus(t, resp, body, http.StatusBadRequest)
			var got struct {
				Fields map[string]string `json:"fields"`
			}
			json.Unmarshal(body, &got)
			if _, ok := got.Fields[tc.field]; !ok {
				t.Fatalf("expected error for field %q, got %s", tc.field, body)
			}
		})
	}

	resp, body := do(t, ts, http.MethodPost, "/books", "{not json")
	expectStatus(t, resp, body, http.StatusBadRequest)

	// Update must validate too.
	createBook(t, ts, bookInput{Title: "T", Author: "A"})
	resp, body = do(t, ts, http.MethodPut, "/books/1", bookInput{Title: "", Author: "A"})
	expectStatus(t, resp, body, http.StatusBadRequest)
}

func TestNotFoundAndBadID(t *testing.T) {
	ts := newTestServer(t)
	valid := bookInput{Title: "T", Author: "A"}

	for _, tc := range []struct {
		method, path string
		body         any
		want         int
	}{
		{http.MethodGet, "/books/999", nil, http.StatusNotFound},
		{http.MethodPut, "/books/999", valid, http.StatusNotFound},
		{http.MethodDelete, "/books/999", nil, http.StatusNotFound},
		{http.MethodGet, "/books/abc", nil, http.StatusBadRequest},
		{http.MethodDelete, "/books/0", nil, http.StatusBadRequest},
		{http.MethodPatch, "/books/1", valid, http.StatusMethodNotAllowed},
	} {
		resp, body := do(t, ts, tc.method, tc.path, tc.body)
		if resp.StatusCode != tc.want {
			t.Errorf("%s %s: status %d, want %d (%s)", tc.method, tc.path, resp.StatusCode, tc.want, body)
		}
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b := Book{Title: "Kept", Author: "Someone"}
	if err := s1.Create(&b); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	got, err := s2.Get(b.ID)
	if err != nil || got.Title != "Kept" {
		t.Fatalf("after reopen: %+v, %v", got, err)
	}
}
