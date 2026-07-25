# ``AsyncKit``

@Metadata {
    @TitleHeading(Package)
}

Provides a set of utilities for working with EventLoopFutures and other pre-Concurrency support APIs.

## Overview

_**AsyncKit is a legacy package; its use is not recommended in new projects.**_

AsyncKit provides a number of extensions to both Swift's Concurrency primitives and NIO's futures to make working with them easier. The long-term goal is to migrate away from this package as Swift Concurrency adds support for working in an asynchronous environment easy.

See references below for usage details.

## Topics

### Legacy connection pools

- ``EventLoopConnectionPool``
- ``EventLoopGroupConnectionPool``
- ``ConnectionPoolSource``
- ``ConnectionPoolItem``
- ``ConnectionPoolError``
- ``ConnectionPoolTimeoutError``

### Optionals

- ``strictMap(_:_:)``
- ``strictMap(_:_:_:)``
- ``strictMap(_:_:_:_:)``
- ``strictMap(_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``
- ``strictMap(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:)``

### EventLoop and EventLoopGroup

- ``NIOCore/EventLoop/flatten(_:)-6gsl5``
- ``NIOCore/EventLoop/flatten(_:)-7tski``
- ``NIOCore/EventLoopGroup/future()``
- ``NIOCore/EventLoopGroup/future(error:)``
- ``NIOCore/EventLoopGroup/future(_:)``
- ``NIOCore/EventLoopGroup/future(result:)``
- ``NIOCore/EventLoopGroup/tryFuture(_:)``

### EventLoopFuture

- ``EventLoopFutureQueue``
- ``NIOCore/EventLoopFuture/mapEach(_:)-3wa2g``
- ``NIOCore/EventLoopFuture/mapEach(_:)-9cwjy``
- ``NIOCore/EventLoopFuture/mapEachCompact(_:)-2vkmo``
- ``NIOCore/EventLoopFuture/mapEachCompact(_:)-4sfs3``
- ``NIOCore/EventLoopFuture/mapEachFlat(_:)-9kgfr``
- ``NIOCore/EventLoopFuture/mapEachFlat(_:)-783z2``
- ``NIOCore/EventLoopFuture/flatMapEach(on:_:)-9yail``
- ``NIOCore/EventLoopFuture/flatMapEach(on:_:)-8yhpe``
- ``NIOCore/EventLoopFuture/flatMapEachCompact(on:_:)``
- ``NIOCore/EventLoopFuture/flatMapEachThrowing(_:)``
- ``NIOCore/EventLoopFuture/flatMapEachCompactThrowing(_:)``
- ``NIOCore/EventLoopFuture/sequencedFlatMapEach(_:)-29ak2``
- ``NIOCore/EventLoopFuture/sequencedFlatMapEach(_:)-6d82b``
- ``NIOCore/EventLoopFuture/sequencedFlatMapEachCompact(_:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/whenTheySucceed(_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:_:file:line:)``
- ``NIOCore/EventLoopFuture/guard(_:else:)``
- ``NIOCore/EventLoopFuture/flatMapAlways(file:line:_:)``
- ``NIOCore/EventLoopFuture/nonempty(orError:)``
- ``NIOCore/EventLoopFuture/nonemptyMap(_:)``
- ``NIOCore/EventLoopFuture/nonemptyMap(or:_:)``
- ``NIOCore/EventLoopFuture/nonemptyFlatMapThrowing(_:)``
- ``NIOCore/EventLoopFuture/nonemptyFlatMapThrowing(or:_:)``
- ``NIOCore/EventLoopFuture/nonemptyFlatMap(_:)``
- ``NIOCore/EventLoopFuture/nonemptyFlatMap(or:_:)``
- ``NIOCore/EventLoopFuture/nonemptyFlatMap(orFlat:_:)``
- ``NIOCore/EventLoopFuture/optionalMap(_:)``
- ``NIOCore/EventLoopFuture/optionalFlatMap(_:)-1lhnd``
- ``NIOCore/EventLoopFuture/optionalFlatMap(_:)-1c1gn``
- ``NIOCore/EventLoopFuture/optionalFlatMapThrowing(_:)``
- ``NIOCore/EventLoopFuture/transform(to:)-7agus``
- ``NIOCore/EventLoopFuture/transform(to:)-3k9qv``
- ``NIOCore/EventLoopFuture/tryFlatMap(file:line:_:)``

### EventLoopFuture operators

- ``NIOCore/EventLoopFuture/+(_:_:)-48eo2``
- ``NIOCore/EventLoopFuture/+(_:_:)-78tv8``
- ``NIOCore/EventLoopFuture/+=(_:_:)-3854m``
- ``NIOCore/EventLoopFuture/+=(_:_:)-1t7oh``
<!--- ``NIOCore/EventLoopFuture/-(_:_:)-92wyb``-->
<!--- ``NIOCore/EventLoopFuture/-=(_:_:)-4sy59``-->
<!--- ``NIOCore/EventLoopFuture/-(_:_:)-6djhk``-->
<!--- ``NIOCore/EventLoopFuture/-=(_:_:)-3v817``-->
- ``NIOCore/EventLoopFuture/*(_:_:)``
- ``NIOCore/EventLoopFuture/*=(_:_:)``
<!--- ``NIOCore/EventLoopFuture//(_:_:)``-->
<!--- ``NIOCore/EventLoopFuture//=(_:_:)``-->
- ``NIOCore/EventLoopFuture/%(_:_:)``
- ``NIOCore/EventLoopFuture/%=(_:_:)``
- ``NIOCore/EventLoopFuture/<(_:_:)``
- ``NIOCore/EventLoopFuture/<=(_:_:)``
- ``NIOCore/EventLoopFuture/>(_:_:)``
- ``NIOCore/EventLoopFuture/>=(_:_:)``
- ``NIOCore/EventLoopFuture/<<(_:_:)``
- ``NIOCore/EventLoopFuture/<<=(_:_:)``
- ``NIOCore/EventLoopFuture/>>(_:_:)``
- ``NIOCore/EventLoopFuture/>>=(_:_:)``
- ``NIOCore/EventLoopFuture/&(_:_:)``
- ``NIOCore/EventLoopFuture/&=(_:_:)``
- ``NIOCore/EventLoopFuture/|(_:_:)``
- ``NIOCore/EventLoopFuture/|=(_:_:)``
- ``NIOCore/EventLoopFuture/^(_:_:)``
- ``NIOCore/EventLoopFuture/^=(_:_:)``
- ``NIOCore/EventLoopFuture/~(_:)``
