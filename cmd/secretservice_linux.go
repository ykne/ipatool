//go:build linux && !ios

package cmd

import (
	"encoding/hex"
	"strings"

	"github.com/godbus/dbus/v5"
)

const (
	secretServiceBusName         = "org.freedesktop.secrets"
	secretServiceObjectPath      = "/org/freedesktop/secrets"
	secretServiceCollectionsProp = "org.freedesktop.Secret.Service.Collections"
	secretServiceLabelProp       = "org.freedesktop.Secret.Collection.Label"
	secretServiceCollectionPath  = secretServiceObjectPath + "/collection/"
)

// secretServiceCollectionName returns the name the keyring library must be
// given to find the Secret Service collection whose label is label, or "" when
// there is no such collection (or no Secret Service).
//
// The keyring library creates the collection with the name as its label, but
// finds it again by comparing a D-Bus object path built from that name with the
// collection's real path. Object paths cannot contain "-" or ".", and daemons
// map them differently (GNOME Keyring escapes them as "_XX", oo7-daemon uses a
// plain "_"), so the lookup fails on some daemons even though the collection
// exists. Looking the collection up by label and deriving the name from its
// real path makes the library's comparison succeed on any daemon.
func secretServiceCollectionName(label string) string {
	conn, err := dbus.SessionBus()
	if err != nil {
		return ""
	}

	value, err := conn.Object(secretServiceBusName, secretServiceObjectPath).GetProperty(secretServiceCollectionsProp)
	if err != nil {
		return ""
	}

	paths, ok := value.Value().([]dbus.ObjectPath)
	if !ok {
		return ""
	}

	for _, path := range paths {
		element, found := strings.CutPrefix(string(path), secretServiceCollectionPath)
		if !found {
			continue
		}

		value, err := conn.Object(secretServiceBusName, path).GetProperty(secretServiceLabelProp)
		if err != nil {
			continue
		}

		if got, ok := value.Value().(string); ok && strings.EqualFold(got, label) {
			return decodeSecretServiceElement(element)
		}
	}

	return ""
}

// decodeSecretServiceElement mirrors the keyring library's path decoding ("_XX"
// is a hex-escaped byte, anything malformed leaves the input unchanged), so the
// result compares equal to what the library computes from the same path.
func decodeSecretServiceElement(src string) string {
	var dst strings.Builder

	for i := 0; i < len(src); i++ {
		if src[i] != '_' {
			dst.WriteByte(src[i])

			continue
		}

		if i+3 > len(src) {
			return src
		}

		decoded, err := hex.DecodeString(src[i+1 : i+3])
		if err != nil {
			return src
		}

		dst.Write(decoded)

		i += 2
	}

	return dst.String()
}
