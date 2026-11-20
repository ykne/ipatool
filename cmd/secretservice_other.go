//go:build !linux && !ios

package cmd

// secretServiceCollectionName is only needed on Linux.
func secretServiceCollectionName(string) string { return "" }
