// Package cmd is the entry point of the tool.
package cmd

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/AdguardTeam/golibs/log"
	"github.com/ameshkov/udptlspipe/internal/pipe"
	"github.com/ameshkov/udptlspipe/internal/version"
	goFlags "github.com/jessevdk/go-flags"
	tls "github.com/refraction-networking/utls"
)

// Main is the entry point for the command-line tool.
func Main() {
	if len(os.Args) == 2 && (os.Args[1] == "--version" || os.Args[1] == "-v") {
		fmt.Printf("udptlspipe version: %s\n", version.Version())

		os.Exit(0)
	}

	o, err := parseOptions()
	var flagErr *goFlags.Error
	if errors.As(err, &flagErr) && flagErr.Type == goFlags.ErrHelp {
		// This is a special case when we exit process here as we received
		// --help.
		os.Exit(0)
	}

	if err != nil {
		log.Error("Failed to parse args: %v", err)

		os.Exit(1)
	}

	if o.Verbose {
		log.SetLevel(log.DEBUG)
	}

	log.Info("Configuration:\n%s", o)

	cfg := &pipe.Config{
		ListenAddr:           o.ListenAddr,
		DestinationAddr:      o.DestinationAddr,
		Password:             o.Password,
		ServerMode:           o.ServerMode,
		ProxyURL:             o.ProxyURL,
		VerifyCertificate:    o.VerifyCertificate,
		TLSServerName:        o.TLSServerName,
		ProbeReverseProxyURL: o.ProbeReverseProxyURL,
	}

	if o.TLSCertPath != "" {
		if !o.ServerMode {
			log.Error("TLS certificate only works in server mode")

			os.Exit(1)
		}

		cert, certErr := loadX509KeyPair(o.TLSCertPath, o.TLSCertKey)
		if certErr != nil {
			log.Error("Failed to load TLS certificate: %v", err)

			os.Exit(1)
		}

		cfg.TLSCertificate = cert
	}

	srv, err := pipe.NewServer(cfg)
	if err != nil {
		log.Error("Failed to initialize server: %v", err)

		os.Exit(1)
	}

	err = srv.Start()
	if err != nil {
		log.Error("Failed to start the server: %v", err)

		os.Exit(1)
	}

	// Subscribe to the OS events.
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, syscall.SIGINT, syscall.SIGTERM)

	// Wait until the user stops the tool.
	<-signalChannel

	// Gracefully shutdown the server.
	ctx, cancel := context.WithDeadline(context.Background(), time.Now().Add(time.Second*10))
	defer cancel()
	err = srv.Shutdown(ctx)
	if err != nil {
		log.Info("Failed to gracefully shutdown the server: %v", err)
	}

	log.Info("Exiting udptlspipe.")
}

// loadX509KeyPair reads and parses a public/private key pair from a pair of
// files.  The files must contain PEM encoded data.  The certificate file may
// contain intermediate certificates following the leaf certificate to form a
// certificate chain.  On successful return, Certificate.Leaf will be nil
// because the parsed form of the certificate is not retained.
func loadX509KeyPair(certFile, keyFile string) (crt *tls.Certificate, err error) {
	// #nosec G304 -- Trust the file path that is given in the configuration.
	certPEMBlock, err := os.ReadFile(certFile)
	if err != nil {
		return nil, err
	}

	// #nosec G304 -- Trust the file path that is given in the configuration.
	keyPEMBlock, err := os.ReadFile(keyFile)
	if err != nil {
		return nil, err
	}

	tlsCert, err := tls.X509KeyPair(certPEMBlock, keyPEMBlock)
	if err != nil {
		return nil, err
	}

	return &tlsCert, nil
}
