//go:build !ios

package cmd

import (
	"github.com/byteness/keyring"
	"github.com/majd/ipatool/v2/pkg/keychain"
)

func openKeyring(config keyring.Config) (keychain.Keyring, error) {
	// Resolve the Secret Service collection by its label first; see
	// secretServiceCollectionName.
	if name := secretServiceCollectionName(config.ServiceName); name != "" {
		config.LibSecretCollectionName = name
	}

	return keyring.Open(config) //nolint:wrapcheck
}
