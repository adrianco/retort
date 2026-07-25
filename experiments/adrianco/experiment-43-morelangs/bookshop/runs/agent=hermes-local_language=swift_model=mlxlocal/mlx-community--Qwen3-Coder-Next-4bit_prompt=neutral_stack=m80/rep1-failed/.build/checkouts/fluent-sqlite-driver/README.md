<p align="center">
<img src="https://design.vapor.codes/images/vapor-fluentsqlitedriver.svg" height="96" alt="FluentSQLiteDriver">
<br>
<br>
<a href="https://docs.vapor.codes/4.0/"><img src="https://design.vapor.codes/images/readthedocs.svg" alt="Documentation"></a>
<a href="https://discord.gg/vapor"><img src="https://design.vapor.codes/images/discordchat.svg" alt="Team Chat"></a>
<a href="LICENSE"><img src="https://design.vapor.codes/images/mitlicense.svg" alt="MIT License"></a>
<a href="https://github.com/vapor/fluent-sqlite-driver/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/vapor/fluent-sqlite-driver/test.yml?event=push&style=plastic&logo=github&label=tests&logoColor=%23ccc" alt="Continuous Integration"></a>
<a href="https://codecov.io/github/vapor/fluent-sqlite-driver"><img src="https://img.shields.io/codecov/c/github/vapor/fluent-sqlite-driver?style=plastic&logo=codecov&label=codecov" alt="Code Coverage"></a>
<a href="https://swift.org"><img src="https://design.vapor.codes/images/swift60up.svg" alt="Swift 6.0+"></a>
</p>

<br>

FluentSQLiteDriver is a [FluentKit] driver for SQLite clients. It provides support for using the Fluent ORM with SQLite databases, and uses [SQLiteKit] to provide [SQLKit] driver services, [SQLiteNIO] to connect and communicate databases asynchronously, and [AsyncKit] to provide connection pooling.

[FluentKit]: https://github.com/vapor/fluent-kit
[SQLKit]: https://github.com/vapor/sql-kit
[SQLiteKit]: https://github.com/vapor/sqlite-kit
[SQLiteNIO]: https://github.com/vapor/sqlite-nio
[AsyncKit]: https://github.com/vapor/async-kit

### Usage

Use the SPM string to easily include the dependendency in your `Package.swift` file:

```swift
.package(url: "https://github.com/vapor/fluent-sqlite-driver.git", from: "4.0.0")
```

For additional information, see [the Fluent documentation](https://docs.vapor.codes/fluent/overview/).
