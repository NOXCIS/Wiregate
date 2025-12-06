// Package version exports some getters for the project's version values.
package version

// Versions

// These are set by the linker.  Unfortunately, we cannot set constants during
// linking, and Go doesn't have a concept of immutable variables, so to be
// thorough we have to only export them through getters.
var (
	version string
)

// Version returns the compiled-in value of this product version as a string.
func Version() (v string) {
	if version == "" {
		return "v0.0"
	}

	return version
}
