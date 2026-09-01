package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore("file::memory:?cache=shared&_pragma=foreign_keys(1)")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	srv := httptest.NewServer(NewRouter(store))
	t.Cleanup(srv.Close)
	return srv
}

func doJSON(t *testing.T, method, url string, body any) (*http.Response, []byte) {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req, err := http.NewRequest(method, url, &buf)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var out bytes.Buffer
	_, _ = out.ReadFrom(resp.Body)
	return resp, out.Bytes()
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, body := doJSON(t, http.MethodGet, srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", resp.StatusCode, body)
	}
	var m map[string]string
	if err := json.Unmarshal(body, &m); err != nil || m["status"] != "ok" {
		t.Fatalf("unexpected body: %s", body)
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)
	resp, body := doJSON(t, http.MethodPost, srv.URL+"/books",
		Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("want 201, got %d: %s", resp.StatusCode, body)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("bad created book: %+v", created)
	}

	resp, body = doJSON(t, http.MethodGet, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", resp.StatusCode, body)
	}
	var got Book
	_ = json.Unmarshal(body, &got)
	if got != created {
		t.Fatalf("get mismatch: got %+v want %+v", got, created)
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := []struct {
		name string
		body any
	}{
		{"missing title", map[string]any{"author": "X"}},
		{"missing author", map[string]any{"title": "X"}},
		{"blank title", map[string]any{"title": "  ", "author": "X"}},
		{"invalid json", "not json"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := doJSON(t, http.MethodPost, srv.URL+"/books", tc.body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("want 400, got %d: %s", resp.StatusCode, body)
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	for _, b := range []Book{
		{Title: "A", Author: "Alice"},
		{Title: "B", Author: "Bob"},
		{Title: "C", Author: "Alice"},
	} {
		if resp, body := doJSON(t, http.MethodPost, srv.URL+"/books", b); resp.StatusCode != 201 {
			t.Fatalf("seed failed: %d %s", resp.StatusCode, body)
		}
	}
	resp, body := doJSON(t, http.MethodGet, srv.URL+"/books", nil)
	var all []Book
	_ = json.Unmarshal(body, &all)
	if resp.StatusCode != 200 || len(all) != 3 {
		t.Fatalf("want 3 books, got %d (%d): %s", len(all), resp.StatusCode, body)
	}
	_, body = doJSON(t, http.MethodGet, srv.URL+"/books?author=Alice", nil)
	var filtered []Book
	_ = json.Unmarshal(body, &filtered)
	if len(filtered) != 2 {
		t.Fatalf("want 2 Alice books, got %d: %s", len(filtered), body)
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("filter leaked: %+v", b)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	doJSON(t, http.MethodPost, srv.URL+"/books", Book{Title: "Old", Author: "Someone"})

	resp, body := doJSON(t, http.MethodPut, srv.URL+"/books/1", Book{Title: "New", Author: "Someone", Year: 2020})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", resp.StatusCode, body)
	}
	var updated Book
	_ = json.Unmarshal(body, &updated)
	if updated.ID != 1 || updated.Title != "New" || updated.Year != 2020 {
		t.Fatalf("bad update: %+v", updated)
	}

	if resp, body := doJSON(t, http.MethodPut, srv.URL+"/books/99", Book{Title: "X", Author: "Y"}); resp.StatusCode != 404 {
		t.Fatalf("update missing: want 404, got %d: %s", resp.StatusCode, body)
	}

	if resp, _ := doJSON(t, http.MethodDelete, srv.URL+"/books/1", nil); resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete: want 204, got %d", resp.StatusCode)
	}
	if resp, _ := doJSON(t, http.MethodGet, srv.URL+"/books/1", nil); resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete: want 404, got %d", resp.StatusCode)
	}
	if resp, _ := doJSON(t, http.MethodDelete, srv.URL+"/books/1", nil); resp.StatusCode != http.StatusNotFound {
		t.Fatalf("double delete: want 404, got %d", resp.StatusCode)
	}
	if resp, _ := doJSON(t, http.MethodGet, srv.URL+"/books/abc", nil); resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad id: want 400, got %d", resp.StatusCode)
	}
}
