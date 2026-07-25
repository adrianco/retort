# ``StructuredFieldValues``

A Swift implementation of the HTTP Structured Header Field Value specification.

Provides parsing and serialization facilities for structured header field values, as well as implementations of `Encoder` and `Decoder` to allow using `Codable` data types as the payloads of HTTP structured header fields.

## Overview

### About Structured Header Field Values

HTTP Structured Header Field Values are a HTTP extension recorded in [RFC 9651](https://www.ietf.org/rfc/rfc9651.html). They provide a set of data types and algorithms for handling HTTP header field values in a consistent way, allowing a single parser and serializer to handle a wide range of header field values.

### Swift HTTP Structured Header Field Values

This package provides a parser and serializer that implement RFC 9651. They are entirely complete, able to handle all valid HTTP structured header field values. This package also provides `Encoder` and `Decoder` objects for working with Codable in Swift. This allows rapid prototyping and experimentation with HTTP structured header field values, as well as interaction with the wider Swift Codable community.

This package provides two top-level modules: `StructuredFieldValues` and `RawStructuredFieldValues`.

This module, `StructuredFieldValues`, uses the related module `RawStructuredFieldValues` to implement `Encoder` and `Decoder`. This interface is friendly and easy to work with.

Users who have performance problems with this solution or have specific representational needs should investigate `RawStructuredFieldValues`.

### Working with Structured Header Field Values

`StructuredFieldValues` has a simple, easy-to-use high-level API for working with structured header field values. To begin with, let's consider the [HTTP Client Hints specification](https://www.rfc-editor.org/rfc/rfc8942.html). This defines the following new header field:

```
The Accept-CH response header field indicates server support for the hints indicated in its value.  Servers wishing to receive user agent information through Client Hints SHOULD add Accept-CH response header to their responses as early as possible.

Accept-CH is a Structured Header. Its value MUST be an sf-list whose members are tokens. Its ABNF is:

    Accept-CH = sf-list

For example:

    Accept-CH: Sec-CH-Example, Sec-CH-Example-2
```

`swift-http-structured-headers` can parse and serialize this field very simply:

```swift
let field = Array("Sec-CH-Example, Sec-CH-Example-2".utf8)

struct AcceptCH: StructuredFieldValue {
    static let structuredFieldType: StructuredFieldType = .list
    
    var items: [String]
}

// Decoding
let decoder = StructuredFieldValueDecoder()
let parsed = try decoder.decode(AcceptCH.self, from: field)

// Encoding
let encoder = StructuredFieldValueEncoder()
let serialized = try encoder.encode(AcceptCH(items: ["Sec-CH-Example", "Sec-CH-Example-2"]))
```

However, structured header field values can be substantially more complex. Structured header fields can make use of 4 containers and 8 base item types. The containers are:

1. Dictionaries. These are top-level elements and associate token keys with values. The values may be items, or may be inner lists, and each value may also have parameters associated with them. `StructuredFieldValues` can model dictionaries as either Swift objects (where the property names are dictionary keys).
2. Lists. These are top-level elements, providing a sequence of items or inner lists. Each item or inner list may have parameters associated with them. `StructuredFieldValues` models these as Swift objects with one key, `items`, that must be a collection of entries.
3. Inner Lists. These are lists that may be sub-entries of a dictionary or a list. The list entries are items, which may have parameters associated with them: additionally, an inner list may have parameters associated with itself as well. `StructuredFieldValues` models these as either Swift `Array`s _or_, if it's important to extract parameters, as a two-field Swift `struct` where one field is called `items` and contains an `Array`, and other field is called `parameters` and contains a dictionary.
4. Parameters. Parameters associate token keys with items without parameters. These are used to store metadata about objects within a field. `StructuredFieldValues` models these as either Swift objects (where the property names are the parameter keys) or as Swift dictionaries.

The base types are:

1. Booleans. `StructuredFieldValues` models these as Swift's `Bool` type.
2. Integers. `StructuredFieldValues` models these as any fixed-width integer type.
3. Decimals. `StructuredFieldValues` models these as any floating-point type, or as Foundation's `Decimal`.
4. Tokens. `StructuredFieldValues` models these as Swift's `String` type, where the range of characters is restricted.
5. Strings. `StructuredFieldValues` models these as Swift's `String` type.
6. Binary data. `StructuredFieldValues` models this as Foundation's `Data` type.
7. Dates. `StructuredFieldValues` models these as Foundation's `Date` type.
8. Display strings. `StructuredFieldValues` models these as the `DisplayString` type which it provides.

For any Structured Header Field Value Item, the item may either be represented directly by the appropriate type, or by a Swift struct with two properties: `item` and `parameters`. This latter mode is how parameters on a given item may be captured.

The top-level Structured Header Field Value must identify what kind of header field it corresponds to by using ``StructuredFieldType``: `.item`, `.list`, or `.dictionary`. This is inherent in the type of the field and will be specified in the relevant field specification.

## Topics

### Declaring Codable Types

- ``StructuredFieldValue``
- ``StructuredFieldType``

### Helper Types

- ``DisplayString``

### Encoding and Decoding

- ``StructuredFieldValueEncoder``
- ``StructuredFieldValueDecoder``
