<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/vapor/sqlite-kit/assets/1130717/81e423ff-d8b7-49f7-8c40-0287b3f025cf">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/vapor/sqlite-kit/assets/1130717/79147036-e050-4a87-be7c-68d6d2c40717">
  <img src="https://github.com/vapor/sqlite-kit/assets/1130717/79147036-e050-4a87-be7c-68d6d2c40717" height="96" alt="SQLiteKit">
</picture> 
<br>
<br>
<a href="https://docs.vapor.codes/4.0/"><img src="https://design.vapor.codes/images/readthedocs.svg" alt="Documentation"></a>
<a href="https://discord.gg/vapor"><img src="https://design.vapor.codes/images/discordchat.svg" alt="Team Chat"></a>
<a href="LICENSE"><img src="https://design.vapor.codes/images/mitlicense.svg" alt="MIT License"></a>
<a href="https://github.com/vapor/sqlite-kit/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/vapor/sqlite-kit/test.yml?event=push&style=plastic&logo=github&label=test&logoColor=%23ccc" alt="Continuous Integration"></a>
<a href="https://codecov.io/github/vapor/sqlite-kit"><img src="https://img.shields.io/codecov/c/github/vapor/sqlite-kit?style=plastic&logo=codecov&label=codecov"></a>
<a href="https://swift.org"><img src="https://design.vapor.codes/images/swift58up.svg" alt="Swift 5.8+"></a>
<a href="https://www.swift.org/sswg/incubation-process.html"><img src="https://design.vapor.codes/images/sswg-graduated.svg" alt="SSWG Incubation Level: Graduated"></a>
</p>

<br>

SQLiteKit is an [SQLKit] driver for SQLite clients. It supports building and serializing SQLite-dialect SQL queries. SQLiteKit uses [SQLiteNIO] to connect and communicate with the database server asynchronously. [AsyncKit] is used to provide connection pooling.

[SQLKit]: https://github.com/vapor/sql-kit
[SQLiteNIO]: https://github.com/vapor/sqlite-nio
[AsyncKit]: https://github.com/vapor/async-kit

### Usage

Use the SPM string to easily include the dependendency in your `Package.swift` file.

```swift
.package(url: "https://github.com/vapor/sqlite-kit.git", from: "4.0.0")
```

### Supported Platforms

SQLiteKit supports the following platforms:

- Ubuntu 20.04+
- macOS 10.15+
