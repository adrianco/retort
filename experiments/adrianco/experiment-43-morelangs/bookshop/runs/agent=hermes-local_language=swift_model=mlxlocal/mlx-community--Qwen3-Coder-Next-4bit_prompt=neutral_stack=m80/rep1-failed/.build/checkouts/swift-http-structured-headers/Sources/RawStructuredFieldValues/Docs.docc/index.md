# ``RawStructuredFieldValues``

A Swift implementation of the HTTP Structured Header Field Value specification.

Provides parsing and serialization facilities for structured header field values.

## Overview

### About Structured Header Field Values

HTTP Structured Header Field Values are a HTTP extension recorded in [RFC 9651](https://www.ietf.org/rfc/rfc9651.html). They provide a set of data types and algorithms for handling HTTP header field values in a consistent way, allowing a single parser and serializer to handle a wide range of header field values.

### Swift HTTP Structured Header Field Values

This package provides a parser and serializer that implement RFC 9651. They are entirely complete, able to handle all valid HTTP structured header field values.

This package provides two top-level modules: `StructuredFieldValues` and `RawStructuredFieldValues`.

This module, `RawStructuredFieldValues`, provides a low-level implementation of a serializer and parser. Both of these have been written to avoid using Foundation, making them suitable for a range of use-cases where Foundation is not available. They rely entirely on the Swift standard library and are implemented as generically as possible. One of the limitations due to the absence of Foundation is that this interface is not capable of performing Base64 encoding or decoding: users are free to bring whatever encoder and decoder they choose to use.

This API is low-level, exposing the raw parse tree as the format for the serializer and parser. This allows high-performance and high-flexibility parsing and serialization, at the cost of being verbose and complex. Users are required to understand the structured header format and to operate the slightly awkward types, but maximal fidelity is retained and the performance overhead is low.

The upper-level module, `StructuredFieldValues`, brings along the `Encoder` and `Decoder` and also adds a dependency on Foundation. This Foundation dependency is necessary to correctly handle the base64 formatting, as well as to provide a good natural container for binary data: `Data`, and for dates: `Date`. This interface is substantially friendlier and easier to work with, using Swift's `Codable` support to provide a great user experience.

In most cases users should prefer to use `StructuredFieldValues` unless they know they need the performance advantages of `RawStructuredFieldValues`. The experience will be much better.

### Working with Structured Header Field Values

`RawStructuredFieldValues` has a powerful API for working with structured header field values.

There are two core types: ``StructuredFieldValueParser`` and ``StructuredFieldValueSerializer``. Rather than work with high-level Swift objects, these two objects either produce or accept a Swift representation of the data tree for a given structured header field.

This exposes the maximum amount of information about the header field. It allows users to handle situations where `Codable` cannot necessarily provide the relevant information, such in cases where dictionary ordering is semantic, or where it's necessary to control whether fields are tokens or strings more closely.

These APIs also have lower overhead than the `StructuredFieldValues` APIs.

The cost is that the APIs are substantially more verbose. As an example, let's consider the [HTTP Client Hints specification](https://www.rfc-editor.org/rfc/rfc8942.html). This defines the following new header field:

```
The Accept-CH response header field indicates server support for the hints indicated in its value.  Servers wishing to receive user agent information through Client Hints SHOULD add Accept-CH response header to their responses as early as possible.

Accept-CH is a Structured Header. Its value MUST be an sf-list whose members are tokens. Its ABNF is:

    Accept-CH = sf-list

For example:

    Accept-CH: Sec-CH-Example, Sec-CH-Example-2
```

To parse or serialize this in `RawStructuredFieldValues` would look like this:

```swift
let field = Array("Sec-CH-Example, Sec-CH-Example-2".utf8)
var parser = StructuredFieldValueParser(field)
let parsed = parser.parseListFieldValue()

print(parsed)
// [
//     .item(Item(bareItem: .token("Sec-CH-Example"), parameters: [])),
//     .item(Item(bareItem: .token("Sec-CH-Example-2"), parameters: [])),
// ]

var serializer = StructuredFieldValueSerializer()
let serialized = serializer.writeListFieldValue(parsed)
```

Notice the substantially more verbose types involved in this operation. These types are highly generic, giving the opportunity for parsing and serializing that greatly reduces the runtime overhead. They also make it easier to distinguish between tokens and strings, and to observe the order of objects in dictionaries or parameters, which can be lost at the Codable level.

In general, users should consider this API only when they are confident they need either the flexibility or the performance. This may be valuable for header fields that do not evolve often, or that are highly dynamic.

## Topics

### Representing Structured Field Values

- ``InnerList``
- ``BareInnerList``
- ``Item``
- ``BareItem``
- ``ItemOrInnerList``

### Helper Types

- ``OrderedMap``
- ``PseudoDecimal``

### Parsing and Serializing

- ``StructuredFieldValueParser``
- ``StructuredFieldValueSerializer``

### Errors

- ``StructuredHeaderError``
