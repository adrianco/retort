<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/vapor/multipart-kit/assets/1130717/4b3aed4e-2b18-4689-80c8-d31ccf169947">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/vapor/multipart-kit/assets/1130717/5c60750b-ef11-4137-9f9e-917ebcc49ca6">
  <img src="https://github.com/vapor/multipart-kit/assets/1130717/5c60750b-ef11-4137-9f9e-917ebcc49ca6" height="96" alt="MultipartKit">
</picture> 
<br>
<br>
<a href="https://docs.vapor.codes/4.0/"><img src="https://design.vapor.codes/images/readthedocs.svg" alt="Documentation"></a>
<a href="https://discord.gg/vapor"><img src="https://design.vapor.codes/images/discordchat.svg" alt="Team Chat"></a>
<a href="LICENSE"><img src="https://design.vapor.codes/images/mitlicense.svg" alt="MIT License"></a>
<a href="https://github.com/vapor/multipart-kit/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/vapor/multipart-kit/test.yml?event=push&style=plastic&logo=github&label=tests&logoColor=%23ccc" alt="Continuous Integration"></a>
<a href="https://codecov.io/github/vapor/multipart-kit"><img src="https://img.shields.io/codecov/c/github/vapor/multipart-kit?style=plastic&logo=codecov&label=Codecov&token=yDzzHja8lt"></a>
<a href="https://swift.org"><img src="https://design.vapor.codes/images/swift57up.svg" alt="Swift 5.7+"></a>
</p>

🏞 Multipart parser and serializer with `Codable` support for Multipart Form Data.

### Installation

Use the SPM string to easily include the dependency in your `Package.swift` file.

Add MultipartKit to your package dependencies:

```swift
dependencies: [
    // ...
    .package(url: "https://github.com/vapor/multipart-kit.git", from: "4.0.0"),
]
```

Add MultipartKit to your target's dependencies:

```swift
targets: [
    .target(name: "MyAppTarget", dependencies: [
        // ...
        .product(name: "MultipartKit", package: "multipart-kit"),
    ])
]
```

### Supported Platforms

MultipartKit supports the following platforms:

- All Linux distributions supported by Swift 5.7+
- macOS 10.15+

## Overview

MultipartKit is a multipart parsing and serializing library. It provides `Codable` support for the special case of the `multipart/form-data` media type through a `FormDataEncoder` and `FormDataDecoder`. The parser delivers its output as it is parsed through callbacks suitable for streaming.

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

We can encode this instance of a our type using a `FormDataEncoder`.

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

In order to _decode_ this message we feed this output and the same boundary to a `FormDataDecoder` and we get back an identical instance to the one we started with.

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
