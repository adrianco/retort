##===----------------------------------------------------------------------===##
##
## This source file is part of the SwiftASN1 open source project
##
## Copyright (c) 2023 Apple Inc. and the SwiftASN1 project authors
## Licensed under Apache License v2.0
##
## See LICENSE.txt for license information
## See CONTRIBUTORS.txt for the list of SwiftASN1 project authors
##
## SPDX-License-Identifier: Apache-2.0
##
##===----------------------------------------------------------------------===##

set(SWIFT_ASN1_EXPORTS_FILE ${CMAKE_CURRENT_BINARY_DIR}/SwiftASN1Exports.cmake)
configure_file(SwiftASN1Config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/SwiftASN1Config.cmake)

get_property(SWIFT_ASN1_EXPORTS GLOBAL PROPERTY SWIFT_ASN1_EXPORTS)
export(TARGETS ${SWIFT_ASN1_EXPORTS} FILE ${SWIFT_ASN1_EXPORTS_FILE})
