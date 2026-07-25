# SwiftASN1

An implementation of ASN.1 types and DER serialization.

## Overview

ASN.1, and the DER encoding scheme, is a commonly used object serialization format. The most common use-cases for ASN.1 in
general computing are in the cryptographic space, but there are a number of use-cases in a wide range of fields. This module
provides an implementation of a number of ASN.1 types, as well as the DER serialization format for ASN.1.

ASN.1 can be used abstractly to describe essentially any kind of object. ASN.1 objects are made up of either primitive or
composite (called "constructed") types. Individual scalar objects can be combined into aggregate types, and composed essentially
arbitrarily to form abstract object formats.

Importantly, the ASN.1 object description does not define a specific encoding for these objects. Instead there are a wide range
of possible ways to serialize or deserialize an ASN.1 object. Some of the most prominent are BER (the Basic Encoding Rules),
CER (the Canonical Encoding Rules), DER (the Distinguished Encoding Rules), and XER (the XML Encoding Rules). For the cryptographic
use-case DER is the standard choice, as a given ASN.1 object can be encoded in only one way under DER. This makes signing and verifying
vastly easier, as it is at least in principle possible to perfectly reconstruct the serialization of a parsed object.

This module provides several moving pieces:

1. A high-level representation of an ASN.1 object, in the form of a tree of object nodes (`ASN1Node`).
2. A DER parser that can construct the ASN.1 tree from serialized bytes (`DER.parse(_:)`).
3. A DER serializer that can construct serialized bytes from the ASN.1 tree (`DER.Serializer`).
4. A number of built-in ASN.1 types, representing common constructs.

These moving pieces combine to provide support for the DER representation of ASN.1 suitable for a wide range of cryptographic uses.

## Getting Started

To use swift-asn1, add the following dependency to your Package.swift:

 ```swift
 dependencies: [
     .package(url: "https://github.com/apple/swift-asn1.git", .upToNextMajor(from: "1.0.0"))
 ]
 ```

 You can then add the specific product dependency to your target:

 ```swift
 dependencies: [
     .product(name: "SwiftASN1", package: "swift-asn1"),
 ]
 ```

Consult [the documentation](https://swiftpackageindex.com/apple/swift-asn1/main/documentation/swiftasn1) for
examples of how to use the code. A number of examples are also present in the repository itself.
