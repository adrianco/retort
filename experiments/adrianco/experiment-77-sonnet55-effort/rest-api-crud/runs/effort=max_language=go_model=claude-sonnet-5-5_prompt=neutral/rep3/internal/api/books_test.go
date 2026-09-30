package api_test

import (
	"encoding/json"
	"net/http"
	"slices"
	"strconv"
	"strings"
	"testing"
)

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`

// TestBookLifecycle walks one book through every endpoint, the way a client would.
func TestBookLifecycle(t *testing.T) {
	h := newHandler(t)

	created := create(t, h, dune)
	create(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	rec := do(t, h, http.MethodGet, "/books", "")
	expect(t, rec, http.StatusOK)
	if got := titles(decode[[]bookJSON](t, rec)); !slices.Equal(got, []string{"Dune", "Emma"}) {
		t.Errorf("list titles = %v, want [Dune Emma]", got)
	}

	rec = do(t, h, http.MethodGet, path, "")
	expect(t, rec, http.StatusOK)
	if got := decode[bookJSON](t, rec); got.Title != "Dune" || got.Author != "Frank Herbert" {
		t.Errorf("GET %s = %+v", path, got)
	}

	rec = do(t, h, http.MethodPut, path, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	expect(t, rec, http.StatusOK)
	if got := decode[bookJSON](t, rec); got.Title != "Dune Messiah" || got.ID != created.ID {
		t.Errorf("PUT %s = %+v", path, got)
	}

	rec = do(t, h, http.MethodGet, "/books?author=frank%20herbert", "")
	expect(t, rec, http.StatusOK)
	if got := titles(decode[[]bookJSON](t, rec)); !slices.Equal(got, []string{"Dune Messiah"}) {
		t.Errorf("filtered titles = %v, want [Dune Messiah]", got)
	}

	expect(t, do(t, h, http.MethodDelete, path, ""), http.StatusNoContent)
	expect(t, do(t, h, http.MethodGet, path, ""), http.StatusNotFound)

	rec = do(t, h, http.MethodGet, "/books", "")
	expect(t, rec, http.StatusOK)
	if got := titles(decode[[]bookJSON](t, rec)); !slices.Equal(got, []string{"Emma"}) {
		t.Errorf("titles after delete = %v, want [Emma]", got)
	}
}

func TestCreateBook(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodPost, "/books", dune)
	expect(t, rec, http.StatusCreated)

	got := decode[bookJSON](t, rec)
	want := bookJSON{ID: got.ID, Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("9780441172719")}
	if got.ID < 1 || got.Title != want.Title || got.Author != want.Author ||
		got.Year == nil || *got.Year != *want.Year || got.ISBN == nil || *got.ISBN != *want.ISBN {
		t.Errorf("created book = %+v, want %+v", got, want)
	}
	if loc, wantLoc := rec.Header().Get("Location"), "/books/"+strconv.FormatInt(got.ID, 10); loc != wantLoc {
		t.Errorf("Location = %q, want %q", loc, wantLoc)
	}

	// The book must really be stored, not merely echoed back.
	fetched := decode[bookJSON](t, do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(got.ID, 10), ""))
	if fetched.Title != "Dune" || fetched.ISBN == nil || *fetched.ISBN != "9780441172719" {
		t.Errorf("stored book = %+v", fetched)
	}
}

func TestCreateBookWithOnlyRequiredFields(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen"}`)
	expect(t, rec, http.StatusCreated)

	// Optional fields are always present in the response, as null when unset.
	fields := decode[map[string]any](t, rec)
	for _, name := range []string{"year", "isbn"} {
		if v, present := fields[name]; !present || v != nil {
			t.Errorf("%s = %v (present: %v), want an explicit null", name, v, present)
		}
	}
}

func TestCreateBookTrimsWhitespace(t *testing.T) {
	h := newHandler(t)

	got := create(t, h, `{"title":"  Dune  ","author":"\tFrank Herbert\n","isbn":"   "}`)
	if got.Title != "Dune" || got.Author != "Frank Herbert" {
		t.Errorf("title/author = %q/%q, want them trimmed", got.Title, got.Author)
	}
	if got.ISBN != nil {
		t.Errorf("blank isbn = %q, want it treated as not provided", *got.ISBN)
	}
}

func TestCreateBookAcceptsUnicodeAndMarkup(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodPost, "/books", `{"title":"Tom & Jerry <3 — 吾輩は猫である","author":"夏目 漱石"}`)
	expect(t, rec, http.StatusCreated)
	if got := decode[bookJSON](t, rec); got.Title != "Tom & Jerry <3 — 吾輩は猫である" || got.Author != "夏目 漱石" {
		t.Errorf("unicode did not round-trip: %+v", got)
	}
	if !strings.Contains(rec.Body.String(), "Tom & Jerry <3 — 吾輩は猫である") {
		t.Errorf("response escapes characters needlessly: %s", rec.Body)
	}
}

func TestCreateBookIgnoresClientSuppliedID(t *testing.T) {
	h := newHandler(t)
	got := create(t, h, `{"id":999,"title":"T","author":"A"}`)
	if got.ID == 999 {
		t.Error("the server accepted a client-chosen ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantError  string
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, "title is required", []string{"title"}},
		{"empty title", `{"title":"","author":"A"}`, "title is required", []string{"title"}},
		{"blank title", `{"title":"   ","author":"A"}`, "title is required", []string{"title"}},
		{"null title", `{"title":null,"author":"A"}`, "title is required", []string{"title"}},
		{"missing author", `{"title":"T"}`, "author is required", []string{"author"}},
		{"empty author", `{"title":"T","author":""}`, "author is required", []string{"author"}},
		{"blank author", `{"title":"T","author":" \t "}`, "author is required", []string{"author"}},
		{"missing both", `{}`, "title is required; author is required", []string{"author", "title"}},
		{"year too small", `{"title":"T","author":"A","year":-1}`, "year must be between 0 and 9999", []string{"year"}},
		{"year too large", `{"title":"T","author":"A","year":10000}`, "year must be between 0 and 9999", []string{"year"}},
		{"title too long", `{"title":"` + strings.Repeat("x", 501) + `","author":"A"}`, "title must be at most 500 characters", []string{"title"}},
		{"author too long", `{"title":"T","author":"` + strings.Repeat("x", 501) + `"}`, "author must be at most 500 characters", []string{"author"}},
		{"isbn too long", `{"title":"T","author":"A","isbn":"` + strings.Repeat("9", 33) + `"}`, "isbn must be at most 32 characters", []string{"isbn"}},
		{"every problem is reported", `{"title":"","author":"","year":-5}`,
			"title is required; author is required; year must be between 0 and 9999", []string{"author", "title", "year"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newHandler(t)

			rec := do(t, h, http.MethodPost, "/books", tt.body)
			expect(t, rec, http.StatusBadRequest)

			got := decode[errorJSON](t, rec)
			if got.Error != tt.wantError {
				t.Errorf("error = %q, want %q", got.Error, tt.wantError)
			}
			var fields []string
			for field := range got.Details {
				fields = append(fields, field)
			}
			slices.Sort(fields)
			if !slices.Equal(fields, tt.wantFields) {
				t.Errorf("details name fields %v, want %v", fields, tt.wantFields)
			}

			if list := decode[[]bookJSON](t, do(t, h, http.MethodGet, "/books", "")); len(list) != 0 {
				t.Errorf("a rejected book was stored: %+v", list)
			}
		})
	}
}

// A NUL at the start of a title looks like an empty title to SQLite. It must be
// turned away as a bad request, not fail later as a database error.
func TestControlCharactersAreABadRequestNotAServerError(t *testing.T) {
	tests := []struct {
		name  string
		book  map[string]any
		field string
	}{
		{"title starting with NUL", map[string]any{"title": "\x00x", "author": "A"}, "title"},
		{"title made only of NULs", map[string]any{"title": "\x00\x00", "author": "A"}, "title"},
		{"author made only of NULs", map[string]any{"title": "T", "author": "\x00"}, "author"},
		{"NUL inside the title", map[string]any{"title": "a\x00b", "author": "A"}, "title"},
		{"newline inside the title", map[string]any{"title": "a\nb", "author": "A"}, "title"},
		{"terminal escape sequence", map[string]any{"title": "\x1b[31mred", "author": "A"}, "title"},
		{"NUL in the isbn", map[string]any{"title": "T", "author": "A", "isbn": "1\x00"}, "isbn"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newHandler(t)
			body, err := json.Marshal(tt.book) // produces the JSON escape for each control character
			if err != nil {
				t.Fatal(err)
			}

			rec := do(t, h, http.MethodPost, "/books", string(body))
			expect(t, rec, http.StatusBadRequest)
			if got := decode[errorJSON](t, rec).Details[tt.field]; got != "must not contain control characters" {
				t.Errorf("details[%q] = %q, want the control-character message", tt.field, got)
			}
			if list := decode[[]bookJSON](t, do(t, h, http.MethodGet, "/books", "")); len(list) != 0 {
				t.Errorf("a rejected book was stored: %+v", list)
			}

			// Updates go through the same validation.
			created := create(t, h, dune)
			rec = do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), string(body))
			expect(t, rec, http.StatusBadRequest)
		})
	}
}

func TestCreateBookAcceptsValuesAtTheLimits(t *testing.T) {
	h := newHandler(t)
	body := `{"title":"` + strings.Repeat("é", 500) + `","author":"` + strings.Repeat("x", 500) +
		`","year":9999,"isbn":"` + strings.Repeat("9", 32) + `"}`
	create(t, h, body) // 500 multi-byte characters are within the limit even though they exceed 500 bytes
	create(t, h, `{"title":"T","author":"A","year":0}`)
}

func TestCreateBookRejectsMalformedBodies(t *testing.T) {
	tests := []struct {
		name         string
		body         string
		wantContains string
	}{
		{"empty body", ``, "must not be empty"},
		{"truncated JSON", `{"title":`, "truncated JSON"},
		{"invalid JSON", `{title: "T"}`, "invalid JSON"},
		{"plain text", `hello`, "invalid JSON"},
		{"array", `[{"title":"T","author":"A"}]`, "must be a JSON object"},
		{"string", `"hello"`, "must be a JSON object"},
		{"number", `42`, "must be a JSON object"},
		{"title of the wrong type", `{"title":123,"author":"A"}`, `field "title" must be a string`},
		{"author of the wrong type", `{"title":"T","author":true}`, `field "author" must be a string`},
		{"year as a string", `{"title":"T","author":"A","year":"1965"}`, `field "year" must be an integer`},
		{"fractional year", `{"title":"T","author":"A","year":1965.5}`, `field "year" must be an integer`},
		{"isbn as a number", `{"title":"T","author":"A","isbn":9780441172719}`, `field "isbn" must be a string`},
		{"two objects", `{"title":"T","author":"A"}{"title":"U","author":"B"}`, "single JSON object"},
		{"trailing garbage", `{"title":"T","author":"A"} nope`, "invalid JSON"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newHandler(t)

			rec := do(t, h, http.MethodPost, "/books", tt.body)
			expect(t, rec, http.StatusBadRequest)
			if got := decode[errorJSON](t, rec).Error; !strings.Contains(got, tt.wantContains) {
				t.Errorf("error = %q, want it to contain %q", got, tt.wantContains)
			}
			if list := decode[[]bookJSON](t, do(t, h, http.MethodGet, "/books", "")); len(list) != 0 {
				t.Errorf("a rejected book was stored: %+v", list)
			}
		})
	}
}

func TestCreateBookRejectsOversizedBody(t *testing.T) {
	h := newHandler(t)
	body := `{"title":"T","author":"A","isbn":"` + strings.Repeat("x", 2<<20) + `"}`

	rec := do(t, h, http.MethodPost, "/books", body)
	expect(t, rec, http.StatusRequestEntityTooLarge)
	if got := decode[errorJSON](t, rec).Error; !strings.Contains(got, "too large") {
		t.Errorf("error = %q, want it to say the body is too large", got)
	}
}

// The limit is exactly 1 MiB: a body of that size is fine, one byte more is not.
func TestRequestBodyLimitIsExactlyOneMebibyte(t *testing.T) {
	const limit = 1 << 20
	padded := func(size int) string {
		body := `{"title":"T","author":"A"}`
		return body + strings.Repeat(" ", size-len(body)) // trailing whitespace is valid JSON
	}

	h := newHandler(t)
	expect(t, do(t, h, http.MethodPost, "/books", padded(limit)), http.StatusCreated)
	expect(t, do(t, h, http.MethodPost, "/books", padded(limit+1)), http.StatusRequestEntityTooLarge)
}

func TestListBooksWhenEmpty(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodGet, "/books", "")
	expect(t, rec, http.StatusOK)
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("body = %s, want [] (an empty array, not null)", got)
	}
}

func TestListBooksFilterByAuthor(t *testing.T) {
	h := newHandler(t)
	create(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	create(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	create(t, h, `{"title":"Persuasion","author":"Jane Austen"}`)
	create(t, h, `{"title":"Children of Dune","author":"Frank Herbert"}`)

	tests := []struct {
		name  string
		query string
		want  []string
	}{
		{"no filter", "", []string{"Dune", "Emma", "Persuasion", "Children of Dune"}},
		{"exact name", "?author=Jane%20Austen", []string{"Emma", "Persuasion"}},
		{"plus as space", "?author=Jane+Austen", []string{"Emma", "Persuasion"}},
		{"ignores case", "?author=frank%20HERBERT", []string{"Dune", "Children of Dune"}},
		{"ignores surrounding whitespace", "?author=%20Jane%20Austen%20", []string{"Emma", "Persuasion"}},
		{"unknown author", "?author=Nobody", []string{}},
		{"part of a name is not enough", "?author=Austen", []string{}},
		{"empty filter means no filter", "?author=", []string{"Dune", "Emma", "Persuasion", "Children of Dune"}},
		{"blank filter means no filter", "?author=%20", []string{"Dune", "Emma", "Persuasion", "Children of Dune"}},
		{"other parameters are ignored", "?page=2", []string{"Dune", "Emma", "Persuasion", "Children of Dune"}},
		{"wildcards are literal", "?author=%25", []string{}},
		{"SQL metacharacters are inert", "?author=%27%20OR%20%271%27%3D%271", []string{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodGet, "/books"+tt.query, "")
			expect(t, rec, http.StatusOK)
			if got := titles(decode[[]bookJSON](t, rec)); !slices.Equal(got, tt.want) {
				t.Errorf("titles = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestListBooksRejectsMalformedQuery(t *testing.T) {
	h := newHandler(t)
	create(t, h, dune)

	// A broken filter must not silently turn into "return everything".
	for _, query := range []string{"?author=%zz", "?author=a;b"} {
		rec := do(t, h, http.MethodGet, "/books"+query, "")
		expect(t, rec, http.StatusBadRequest)
		if got := decode[errorJSON](t, rec).Error; got != "malformed query string" {
			t.Errorf("GET /books%s error = %q", query, got)
		}
	}
}

func TestGetBookNotFound(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodGet, "/books/999", "")
	expect(t, rec, http.StatusNotFound)
	if got := decode[errorJSON](t, rec).Error; got != "book not found" {
		t.Errorf("error = %q, want %q", got, "book not found")
	}
}

func TestBookIDMustBeAPositiveInteger(t *testing.T) {
	h := newHandler(t)
	create(t, h, dune)

	for _, id := range []string{"abc", "0", "-1", "1.5", "1e3", "0x1", "99999999999999999999", "%20"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			body := ""
			if method == http.MethodPut {
				body = dune
			}
			rec := do(t, h, method, "/books/"+id, body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s = %d, want 400; body: %s", method, id, rec.Code, rec.Body)
				continue
			}
			if got := decode[errorJSON](t, rec).Error; got != "book id must be a positive integer" {
				t.Errorf("%s /books/%s error = %q", method, id, got)
			}
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newHandler(t)
	created := create(t, h, dune)
	other := create(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	rec := do(t, h, http.MethodPut, path,
		`{"title":"Dune Messiah","author":"F. Herbert","year":1969,"isbn":"9780593098233"}`)
	expect(t, rec, http.StatusOK)
	want := bookJSON{ID: created.ID, Title: "Dune Messiah", Author: "F. Herbert", Year: ptr(1969), ISBN: ptr("9780593098233")}
	got := decode[bookJSON](t, rec)
	if got.ID != want.ID || got.Title != want.Title || got.Author != want.Author ||
		got.Year == nil || *got.Year != *want.Year || got.ISBN == nil || *got.ISBN != *want.ISBN {
		t.Errorf("PUT response = %+v, want %+v", got, want)
	}

	fetched := decode[bookJSON](t, do(t, h, http.MethodGet, path, ""))
	if fetched.Title != "Dune Messiah" || fetched.Author != "F. Herbert" {
		t.Errorf("update was not stored: %+v", fetched)
	}
	untouched := decode[bookJSON](t, do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(other.ID, 10), ""))
	if untouched.Title != "Emma" {
		t.Errorf("update changed another book: %+v", untouched)
	}
}

// PUT replaces the whole resource, so optional fields left out are cleared.
func TestUpdateBookReplacesOptionalFields(t *testing.T) {
	h := newHandler(t)
	created := create(t, h, dune)

	rec := do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), `{"title":"Dune","author":"Frank Herbert"}`)
	expect(t, rec, http.StatusOK)
	if got := decode[bookJSON](t, rec); got.Year != nil || got.ISBN != nil {
		t.Errorf("year/isbn = %v/%v after a PUT that omitted them, want null", got.Year, got.ISBN)
	}
}

func TestUpdateBookIgnoresBodyID(t *testing.T) {
	h := newHandler(t)
	first := create(t, h, dune)
	second := create(t, h, `{"title":"Emma","author":"Jane Austen"}`)

	rec := do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(first.ID, 10),
		`{"id":`+strconv.FormatInt(second.ID, 10)+`,"title":"Changed","author":"A"}`)
	expect(t, rec, http.StatusOK)
	if got := decode[bookJSON](t, rec); got.ID != first.ID || got.Title != "Changed" {
		t.Errorf("PUT response = %+v, want book %d updated", got, first.ID)
	}
	if untouched := decode[bookJSON](t, do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(second.ID, 10), "")); untouched.Title != "Emma" {
		t.Errorf("the ID in the body redirected the update to another book: %+v", untouched)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodPut, "/books/999", dune)
	expect(t, rec, http.StatusNotFound)
	if got := decode[errorJSON](t, rec).Error; got != "book not found" {
		t.Errorf("error = %q, want %q", got, "book not found")
	}
	if list := decode[[]bookJSON](t, do(t, h, http.MethodGet, "/books", "")); len(list) != 0 {
		t.Errorf("PUT to a missing ID created %+v", list)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	tests := []struct {
		name string
		body string
		want int
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest},
		{"blank title", `{"title":"  ","author":"A"}`, http.StatusBadRequest},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest},
		{"empty object", `{}`, http.StatusBadRequest},
		{"invalid year", `{"title":"T","author":"A","year":-3}`, http.StatusBadRequest},
		{"invalid JSON", `not json`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newHandler(t)
			created := create(t, h, dune)
			path := "/books/" + strconv.FormatInt(created.ID, 10)

			rec := do(t, h, http.MethodPut, path, tt.body)
			expect(t, rec, tt.want)
			if decode[errorJSON](t, rec).Error == "" {
				t.Error("error response has no message")
			}

			unchanged := decode[bookJSON](t, do(t, h, http.MethodGet, path, ""))
			if unchanged.Title != "Dune" || unchanged.Author != "Frank Herbert" || unchanged.Year == nil || *unchanged.Year != 1965 {
				t.Errorf("a rejected update changed the book: %+v", unchanged)
			}
		})
	}
}

func TestDeleteBook(t *testing.T) {
	h := newHandler(t)
	doomed := create(t, h, dune)
	kept := create(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	path := "/books/" + strconv.FormatInt(doomed.ID, 10)

	rec := do(t, h, http.MethodDelete, path, "")
	expect(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has a body: %q", rec.Body)
	}

	expect(t, do(t, h, http.MethodGet, path, ""), http.StatusNotFound)
	expect(t, do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(kept.ID, 10), ""), http.StatusOK)

	// Deleting twice is a 404, not a silent success.
	rec = do(t, h, http.MethodDelete, path, "")
	expect(t, rec, http.StatusNotFound)
	if got := decode[errorJSON](t, rec).Error; got != "book not found" {
		t.Errorf("error = %q, want %q", got, "book not found")
	}
}

func TestDeletedIDsAreNotReused(t *testing.T) {
	h := newHandler(t)
	first := create(t, h, dune)
	expect(t, do(t, h, http.MethodDelete, "/books/"+strconv.FormatInt(first.ID, 10), ""), http.StatusNoContent)

	second := create(t, h, dune)
	if second.ID == first.ID {
		t.Errorf("ID %d was handed out again after its book was deleted", first.ID)
	}
}

func TestBookJSONHasExactlyTheDocumentedKeys(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodPost, "/books", dune)
	expect(t, rec, http.StatusCreated)

	var fields map[string]json.RawMessage
	if err := json.Unmarshal(rec.Body.Bytes(), &fields); err != nil {
		t.Fatal(err)
	}
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	if want := []string{"author", "id", "isbn", "title", "year"}; !slices.Equal(keys, want) {
		t.Errorf("response keys = %v, want %v", keys, want)
	}
}
