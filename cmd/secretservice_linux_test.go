//go:build linux && !ios

package cmd

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Secret Service collection names", func() {
	DescribeTable("decodeSecretServiceElement",
		func(path, expected string) {
			Expect(decodeSecretServiceElement(path)).To(Equal(expected))
		},
		// GNOME Keyring escapes "-" and "." as "_XX".
		Entry("gnome-keyring escapes", "ipatool_2dauth_2eservice", "ipatool-auth.service"),
		// oo7-daemon replaces them with a plain "_", which is not decodable.
		Entry("oo7-daemon underscores", "ipatool_auth_service", "ipatool_auth_service"),
		Entry("plain name", "login", "login"),
		Entry("truncated escape", "name_2", "name_2"),
	)
})
