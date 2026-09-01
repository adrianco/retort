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
		t.Fatal(err)
	}
	t.Cleanup(func() { store.Close() })
	srv := httptest.NewServer(NewRouter(store))
	t.Cleanup(srv.Close)
	return srv
}

func do(t *testing.T, method, url string, body any) (*http.Response, []byte) {
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
	out.ReadFrom(resp.Body)
	return resp, out.Bytes()
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, body := do(t, http.MethodGet, srv.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", resp.StatusCode, body)
	}
	var m map[string]string
	json.Unmarshal(body, &m)
	if m["status"] != "ok" {
		t.Fatalf("body = %s", body)
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)
	resp, body := do(t, http.MethodPost, srv.URL+"/books",
		Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("status = %d, want 201: %s", resp.StatusCode, body)
	}
	var created Book
	json.Unmarshal(body, &created)
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	resp, body = do(t, http.MethodGet, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", resp.StatusCode, body)
	}
	var got Book
	json.Unmarshal(body, &got)
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)
	for _, b := range []Book{{Author: "x"}, {Title: "x"}} {
		resp, body := do(t, http.MethodPost, srv.URL+"/books", b)
		if resp.StatusCode != http.StatusBadRequest {
			t.Fatalf("status = %d, want 400 for %+v: %s", resp.StatusCode, b, body)
		}
	}
	resp, _ := do(t, http.MethodGet, srv.URL+"/books/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", resp.StatusCode)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	do(t, http.MethodPost, srv.URL+"/books", Book{Title: "A", Author: "Alice"})
	do(t, http.MethodPost, srv.URL+"/books", Book{Title: "B", Author: "Bob"})
	do(t, http.MethodPost, srv.URL+"/books", Book{Title: "C", Author: "Alice"})

	_, body := do(t, http.MethodGet, srv.URL+"/books", nil)
	var all []Book
	json.Unmarshal(body, &all)
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}
	_, body = do(t, http.MethodGet, srv.URL+"/books?author=Alice", nil)
	var filtered []Book
	json.Unmarshal(body, &filtered)
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2: %s", len(filtered), body)
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("unexpected book %+v", b)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	do(t, http.MethodPost, srv.URL+"/books", Book{Title: "Old", Author: "Someone"})

	resp, body := do(t, http.MethodPut, srv.URL+"/books/1", Book{Title: "New", Author: "Someone", Year: 2000})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", resp.StatusCode, body)
	}
	var updated Book
	json.Unmarshal(body, &updated)
	if updated.Title != "New" || updated.Year != 2000 || updated.ID != 1 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	resp, _ = do(t, http.MethodPut, srv.URL+"/books/99", Book{Title: "X", Author: "Y"})
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}

	resp, _ = do(t, http.MethodDelete, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", resp.StatusCode)
	}
	resp, _ = do(t, http.MethodGet, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}
	resp, _ = do(t, http.MethodDelete, srv.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("delete again status = %d, want 404", resp.StatusCode)
	}
}
