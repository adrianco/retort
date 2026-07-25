# ``MultipartKit``

Parser, serializer, and `Codable` support for `multipart/form-data`.

MultipartKit is a Swift package for parsing and serializing `multipart/form-data` requests. It provides hooks for encoding and decoding requests in Swift and `Codable` support for handling `multipart/form-data` data through a ``FormDataEncoder`` and ``FormDataDecoder``. The parser delivers its output as it is parsed through callbacks suitable for streaming.

### Multipart Form Data

Let's define a `Codable` type and a choose a boundary used to separate the multipart parts.

```swift
struct User: Codable {
    let name: String
    let email: String
}
let user = User(name: "Ed", email: "ed@example.com")
let boundary = "abc123"
```

We can encode this instance of a our type using a ``FormDataEncoder``.

```swift
let encoded = try FormDataEncoder().encode(foo, boundary: boundary)
```

The output looks then looks like this.
```
--abc123
Content-Disposition: form-data; name="name"

Ed
--abc123
Content-Disposition: form-data; name="email"

ed@example.com
--abc123--
```

In order to _decode_ this message we feed this output and the same boundary to a ``FormDataDecoder`` and we get back an identical instance to the one we started with.

```swift
let decoded = try FormDataDecoder().decode(User.self, from: encoded, boundary: boundary)
```

### A note on `null`
As there is no standard defined for how to represent `null` in Multipart (unlike, for instance, JSON), FormDataEncoder and FormDataDecoder do not support encoding or decoding `null` respectively. 

### Nesting and Collections

Nested structures can be represented by naming the parts such that they describe a path using square brackets to denote contained properties or elements in a collection. The following example shows what that looks like in practice.

```swift
struct Nested: Encodable {
    let tag: String
    let flag: Bool
    let nested: [Nested]
}
let boundary = "abc123"
let nested = Nested(tag: "a", flag: true, nested: [Nested(tag: "b", flag: false, nested: [])])
let encoded = try FormDataEncoder().encode(nested, boundary: boundary)
```

This results in the content below.

```
--abc123
Content-Disposition: form-data; name="tag"

a
--abc123
Content-Disposition: form-data; name="flag"

true
--abc123
Content-Disposition: form-data; name="nested[0][tag]"

b
--abc123
Content-Disposition: form-data; name="nested[0][flag]"

false
--abc123--
```

Note that the array elements always include the index (as opposed to just `[]`) in order to support complex nesting.

