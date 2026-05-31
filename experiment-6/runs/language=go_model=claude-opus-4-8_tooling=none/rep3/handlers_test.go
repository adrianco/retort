package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

// newTestServer spins up an in-memory store and HTTP test server.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	ts := httptest.NewServer(NewServer(store).Routes())
	t.Cleanup(ts.Close)
	return ts
}

func createBook(t *testing.T, base string, body string) *http.Response {
	t.Helper()
	resp, err := http.Post(base+"/books", "application/json", bytes.NewBufferString(body))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	return resp
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, err := http.Get(ts.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
	var got map[string]string
	json.NewDecoder(resp.Body).Decode(&got)
	if got["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)
	resp := createBook(t, ts.URL, `{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"123"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, want 201", resp.StatusCode)
	}
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "Go in Action" || created.Author != "Kennedy" {
		t.Fatalf("unexpected book: %+v", created)
	}

	// Fetch it back.
	getResp, err := http.Get(ts.URL + "/books/" + strconv.FormatInt(created.ID, 10))
	if err != nil {
		t.Fatalf("GET /books/{id}: %v", err)
	}
	defer getResp.Body.Close()
	if getResp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, want 200", getResp.StatusCode)
	}
	var fetched Book
	json.NewDecoder(getResp.Body).Decode(&fetched)
	if fetched != created {
		t.Fatalf("fetched %+v, want %+v", fetched, created)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)
	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"X"}`},
		{"missing author", `{"title":"X"}`},
		{"empty body", `{}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp := createBook(t, ts.URL, tc.body)
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400", resp.StatusCode)
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)
	createBook(t, ts.URL, `{"title":"A","author":"Alice"}`).Body.Close()
	createBook(t, ts.URL, `{"title":"B","author":"Bob"}`).Body.Close()
	createBook(t, ts.URL, `{"title":"C","author":"Alice"}`).Body.Close()

	resp, err := http.Get(ts.URL + "/books?author=Alice")
	if err != nil {
		t.Fatalf("GET /books: %v", err)
	}
	defer resp.Body.Close()
	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 2 {
		t.Fatalf("got %d books, want 2", len(books))
	}
	for _, b := range books {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q in filtered result", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestServer(t)
	resp := createBook(t, ts.URL, `{"title":"Old","author":"Auth"}`)
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	req, _ := http.NewRequest(http.MethodPut,
		ts.URL+"/books/"+strconv.FormatInt(created.ID, 10),
		bytes.NewBufferString(`{"title":"New","author":"Auth","year":2020,"isbn":"999"}`))
	req.Header.Set("Content-Type", "application/json")
	putResp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("PUT: %v", err)
	}
	defer putResp.Body.Close()
	if putResp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, want 200", putResp.StatusCode)
	}
	var updated Book
	json.NewDecoder(putResp.Body).Decode(&updated)
	if updated.Title != "New" || updated.Year != 2020 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
}

func TestDeleteBook(t *testing.T) {
	ts := newTestServer(t)
	resp := createBook(t, ts.URL, `{"title":"Doomed","author":"Auth"}`)
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	resp.Body.Close()

	url := ts.URL + "/books/" + strconv.FormatInt(created.ID, 10)
	req, _ := http.NewRequest(http.MethodDelete, url, nil)
	delResp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("DELETE: %v", err)
	}
	delResp.Body.Close()
	if delResp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", delResp.StatusCode)
	}

	// It should now be gone.
	getResp, err := http.Get(url)
	if err != nil {
		t.Fatalf("GET after delete: %v", err)
	}
	defer getResp.Body.Close()
	if getResp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete = %d, want 404", getResp.StatusCode)
	}
}

func TestGetNotFound(t *testing.T) {
	ts := newTestServer(t)
	resp, err := http.Get(ts.URL + "/books/99999")
	if err != nil {
		t.Fatalf("GET: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", resp.StatusCode)
	}
}
