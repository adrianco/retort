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
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	ts := httptest.NewServer(NewRouter(store))
	t.Cleanup(func() { ts.Close(); store.Close() })
	return ts
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
	ts := newTestServer(t)
	resp, body := doJSON(t, http.MethodGet, ts.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
	var got map[string]string
	if err := json.Unmarshal(body, &got); err != nil || got["status"] != "ok" {
		t.Fatalf("body = %s", body)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)
	in := BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	resp, body := doJSON(t, http.MethodPost, ts.URL+"/books", in)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, body = %s", resp.StatusCode, body)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != in.Title || created.Author != in.Author || created.Year != in.Year || created.ISBN != in.ISBN {
		t.Fatalf("created = %+v", created)
	}

	resp, body = doJSON(t, http.MethodGet, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, body = %s", resp.StatusCode, body)
	}
	var got Book
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatal(err)
	}
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)
	cases := []struct {
		name string
		body any
	}{
		{"missing title", BookInput{Author: "Someone"}},
		{"missing author", BookInput{Title: "Something"}},
		{"whitespace title", BookInput{Title: "   ", Author: "Someone"}},
		{"bad year", BookInput{Title: "T", Author: "A", Year: -5}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := doJSON(t, http.MethodPost, ts.URL+"/books", tc.body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status = %d, body = %s", resp.StatusCode, body)
			}
			var got map[string]string
			if err := json.Unmarshal(body, &got); err != nil || got["error"] == "" {
				t.Fatalf("expected error message, body = %s", body)
			}
		})
	}

	// Malformed JSON.
	req, _ := http.NewRequest(http.MethodPost, ts.URL+"/books", bytes.NewBufferString("{not json"))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("malformed JSON status = %d", resp.StatusCode)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)
	for _, b := range []BookInput{
		{Title: "Dune", Author: "Frank Herbert", Year: 1965},
		{Title: "Children of Dune", Author: "Frank Herbert", Year: 1976},
		{Title: "Neuromancer", Author: "William Gibson", Year: 1984},
	} {
		if resp, body := doJSON(t, http.MethodPost, ts.URL+"/books", b); resp.StatusCode != http.StatusCreated {
			t.Fatalf("seed failed: %d %s", resp.StatusCode, body)
		}
	}

	resp, body := doJSON(t, http.MethodGet, ts.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list status = %d", resp.StatusCode)
	}
	var all []Book
	if err := json.Unmarshal(body, &all); err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	resp, body = doJSON(t, http.MethodGet, ts.URL+"/books?author=Frank+Herbert", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("filtered status = %d", resp.StatusCode)
	}
	var filtered []Book
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2; body = %s", len(filtered), body)
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Fatalf("unexpected author %q", b.Author)
		}
	}

	_, body = doJSON(t, http.MethodGet, ts.URL+"/books?author=Nobody", nil)
	if string(bytes.TrimSpace(body)) != "[]" {
		t.Fatalf("empty filter body = %s, want []", body)
	}
}

func TestUpdateAndDelete(t *testing.T) {
	ts := newTestServer(t)
	resp, _ := doJSON(t, http.MethodPost, ts.URL+"/books", BookInput{Title: "Old", Author: "A"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d", resp.StatusCode)
	}

	resp, body := doJSON(t, http.MethodPut, ts.URL+"/books/1", BookInput{Title: "New", Author: "B", Year: 2000, ISBN: "123"})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, body = %s", resp.StatusCode, body)
	}
	var updated Book
	if err := json.Unmarshal(body, &updated); err != nil {
		t.Fatal(err)
	}
	if updated.Title != "New" || updated.Author != "B" || updated.Year != 2000 || updated.ISBN != "123" {
		t.Fatalf("updated = %+v", updated)
	}

	// Update validation still applies.
	resp, _ = doJSON(t, http.MethodPut, ts.URL+"/books/1", BookInput{Title: "", Author: "B"})
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("invalid update status = %d, want 400", resp.StatusCode)
	}

	resp, _ = doJSON(t, http.MethodDelete, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodGet, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodDelete, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("second delete status = %d, want 404", resp.StatusCode)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	ts := newTestServer(t)
	resp, _ := doJSON(t, http.MethodGet, ts.URL+"/books/999", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodPut, ts.URL+"/books/999", BookInput{Title: "T", Author: "A"})
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodGet, ts.URL+"/books/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad id status = %d, want 400", resp.StatusCode)
	}
}
