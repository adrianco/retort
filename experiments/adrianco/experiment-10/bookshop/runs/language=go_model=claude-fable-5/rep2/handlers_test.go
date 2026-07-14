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
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	ts := httptest.NewServer(NewRouter(store))
	t.Cleanup(ts.Close)
	return ts
}

func doJSON(t *testing.T, method, url string, body any) *http.Response {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req, err := http.NewRequest(method, url, &buf)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	t.Cleanup(func() { resp.Body.Close() })
	return resp
}

func decode[T any](t *testing.T, resp *http.Response) T {
	t.Helper()
	var v T
	if err := json.NewDecoder(resp.Body).Decode(&v); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	return v
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp := doJSON(t, http.MethodGet, ts.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
	body := decode[map[string]string](t, resp)
	if body["status"] != "ok" {
		t.Errorf("status = %q, want %q", body["status"], "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)

	resp := doJSON(t, http.MethodPost, ts.URL+"/books", Book{
		Title: "Sun Performance and Tuning", Author: "Adrian Cockcroft", Year: 1998, ISBN: "978-0130952493",
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, want 201", resp.StatusCode)
	}
	created := decode[Book](t, resp)
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}

	resp = doJSON(t, http.MethodGet, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, want 200", resp.StatusCode)
	}
	got := decode[Book](t, resp)
	if got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)

	for _, tc := range []struct {
		name string
		body Book
	}{
		{"missing title", Book{Author: "Someone"}},
		{"missing author", Book{Title: "Untitled"}},
		{"blank title", Book{Title: "   ", Author: "Someone"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			resp := doJSON(t, http.MethodPost, ts.URL+"/books", tc.body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Errorf("status = %d, want 400", resp.StatusCode)
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	for _, b := range []Book{
		{Title: "Book One", Author: "Alice", Year: 2001},
		{Title: "Book Two", Author: "Bob", Year: 2002},
		{Title: "Book Three", Author: "Alice", Year: 2003},
	} {
		if resp := doJSON(t, http.MethodPost, ts.URL+"/books", b); resp.StatusCode != http.StatusCreated {
			t.Fatalf("seed create status = %d", resp.StatusCode)
		}
	}

	resp := doJSON(t, http.MethodGet, ts.URL+"/books", nil)
	if all := decode[[]Book](t, resp); len(all) != 3 {
		t.Errorf("list all: got %d books, want 3", len(all))
	}

	resp = doJSON(t, http.MethodGet, ts.URL+"/books?author=Alice", nil)
	filtered := decode[[]Book](t, resp)
	if len(filtered) != 2 {
		t.Fatalf("filtered: got %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("filtered result has author %q, want Alice", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestServer(t)

	resp := doJSON(t, http.MethodPost, ts.URL+"/books", Book{Title: "Old Title", Author: "Alice"})
	created := decode[Book](t, resp)

	resp = doJSON(t, http.MethodPut, ts.URL+"/books/1", Book{Title: "New Title", Author: "Alice", Year: 2020})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, want 200", resp.StatusCode)
	}
	updated := decode[Book](t, resp)
	if updated.ID != created.ID || updated.Title != "New Title" || updated.Year != 2020 {
		t.Errorf("updated = %+v", updated)
	}

	resp = doJSON(t, http.MethodPut, ts.URL+"/books/999", Book{Title: "X", Author: "Y"})
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("update missing: status = %d, want 404", resp.StatusCode)
	}
}

func TestDeleteBook(t *testing.T) {
	ts := newTestServer(t)

	resp := doJSON(t, http.MethodPost, ts.URL+"/books", Book{Title: "Doomed", Author: "Alice"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d", resp.StatusCode)
	}

	if resp = doJSON(t, http.MethodDelete, ts.URL+"/books/1", nil); resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", resp.StatusCode)
	}
	if resp = doJSON(t, http.MethodGet, ts.URL+"/books/1", nil); resp.StatusCode != http.StatusNotFound {
		t.Errorf("get after delete: status = %d, want 404", resp.StatusCode)
	}
	if resp = doJSON(t, http.MethodDelete, ts.URL+"/books/1", nil); resp.StatusCode != http.StatusNotFound {
		t.Errorf("double delete: status = %d, want 404", resp.StatusCode)
	}
}

func TestGetInvalidID(t *testing.T) {
	ts := newTestServer(t)
	resp := doJSON(t, http.MethodGet, ts.URL+"/books/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", resp.StatusCode)
	}
}
