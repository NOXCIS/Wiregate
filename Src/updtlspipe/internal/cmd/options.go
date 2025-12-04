package cmd

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"

	goFlags "github.com/jessevdk/go-flags"
)

// Options represents command-line arguments.
type Options struct {
	// ServerMode controls whether the tool works in the server mode.
	// By default, the tool will work in the client mode.
	ServerMode bool `yaml:"server" short:"s" long:"server" description:"Enables the server mode (optional). By default it runs in client mode." optional:"yes" optional-value:"true"`

	// ListenAddr is the address the tool will be listening to. If it's in the
	// pipe mode, it will listen to tcp://, if it's in the client mode, it
	// will listen to udp://.
	ListenAddr string `yaml:"listen" short:"l" long:"listen" description:"Address the tool will be listening to (required)." value-name:"<IP:Port>" required:"true"`

	// DestinationAddr is the address the tool will connect to. Depending on the
	// mode (pipe or client) this address has different semantics. In the
	// client mode this is the address of the udptlspipe pipe. In the pipe
	// mode this is the address where the received traffic will be passed.
	DestinationAddr string `yaml:"destination" short:"d" long:"destination" description:"Address the tool will connect to (required)." value-name:"<IP:Port>" required:"true"`

	// Password is used to detect if the client is actually allowed to use
	// udptlspipe. If it's not allowed, the server returns a stub web page.
	Password string `yaml:"password" short:"p" long:"password" description:"Password is used to detect if the client is allowed (optional)." value-name:"<password>"`

	// ProxyURL is the proxy address that should be used when connecting to the
	// destination address.
	ProxyURL string `yaml:"proxy" short:"x" long:"proxy" description:"URL of a proxy to use when connecting to the destination address (optional)." value-name:"[protocol://username:password@]host[:port]"`

	// VerifyCertificate enables server certificate verification in client mode.
	// If enabled, the client will verify the server certificate using the
	// system root certs store.
	VerifyCertificate bool `yaml:"secure" long:"secure" description:"Enables server TLS certificate verification in client mode (optional)." optional:"yes" optional-value:"true"`

	// TLSServerName configures the server name to send in TLS ClientHello when
	// operating in client mode and the server name that will be used when
	// generating a stub certificate. If not set, the default domain name will
	// be used for these purposes.
	TLSServerName string `yaml:"tls-servername" long:"tls-servername" description:"Configures TLS server name that will be sent in the TLS ClientHello in client mode, and the stub certificate name in server mode. If not set, the the default domain name (example.org) will be used (optional)." value-name:"<hostname>"`

	// TLSCertPath is a path to the TLS certificate file. Allows to use a custom
	// certificate in server mode. If not set, the server will generate a
	// self-signed stub certificate.
	TLSCertPath string `yaml:"tls-certfile" long:"tls-certfile" description:"Path to the TLS certificate file. Allows to use a custom certificate in server mode. If not set, the server will generate a self-signed stub certificate (optional)." value-name:"<path-to-cert-file>"`

	// TLSCertKey is a path to the file with the private key to the TLS
	// certificate specified by TLSCertPath.
	TLSCertKey string `yaml:"tls-keyfile" long:"tls-keyfile" description:"Path to the private key for the cert specified in tls-certfile." value-name:"<path-to-key-file>"`

	// ProbeReverseProxyURL is the URL that will be used by the reverse HTTP
	// proxy to respond to unauthorized or proxy requests. If not specified,
	// it will respond with a stub page 403 Forbidden.
	ProbeReverseProxyURL string `yaml:"probe-reverseproxyurl" long:"probe-reverseproxyurl" description:"Unauthorized requests and probes will be proxied to the URL." value-name:"<hostname>"`

	// Verbose defines whether we should write the DEBUG-level log or not.
	Verbose bool `yaml:"verbose" short:"v" long:"verbose" description:"Verbose output (optional)." optional:"yes" optional-value:"true"`
}

// type check
var _ fmt.Stringer = (*Options)(nil)

// String implements the fmt.Stringer interface for *Options.
func (o *Options) String() (str string) {
	b, err := yaml.Marshal(o)
	if err != nil {
		return fmt.Sprintf("Failed to stringify options due to %s", err)
	}

	return string(b)
}

// parseOptions parses os.Args and creates the Options struct.
func parseOptions() (o *Options, err error) {
	opts := &Options{}
	parser := goFlags.NewParser(opts, goFlags.Default|goFlags.IgnoreUnknown)
	remainingArgs, err := parser.ParseArgs(os.Args[1:])
	if err != nil {
		return nil, err
	}

	if len(remainingArgs) > 0 {
		return nil, fmt.Errorf("unknown arguments: %v", remainingArgs)
	}

	return opts, nil
}
