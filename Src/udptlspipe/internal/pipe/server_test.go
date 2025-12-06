package pipe_test

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"testing"
	"time"

	tls "github.com/refraction-networking/utls"

	"github.com/AdguardTeam/golibs/log"
	"github.com/ameshkov/udptlspipe/internal/pipe"
	"github.com/ameshkov/udptlspipe/internal/testutil"
	"github.com/stretchr/testify/require"
)

func TestServer_Start_integration(t *testing.T) {
	// Start the echo server where the pipe will proxy data.
	udpSrv := &testutil.UDPEchoServer{}
	err := udpSrv.Start()
	require.NoError(t, err)
	defer log.OnCloserError(udpSrv, log.DEBUG)

	// Create the pipe server proxying data to that UDP echo server.
	pipeServer, err := pipe.NewServer(&pipe.Config{
		ListenAddr:      "127.0.0.1:0",
		DestinationAddr: udpSrv.Addr(),
		Password:        "123123",
		ServerMode:      true,
	})
	require.NoError(t, err)

	// Start the pipe server, it's ready to accept new connections.
	err = pipeServer.Start()
	require.NoError(t, err)
	defer func() {
		require.NoError(t, pipeServer.Shutdown(context.Background()))
	}()

	// Now create the pipe client connected to that server.
	pipeClient, err := pipe.NewServer(&pipe.Config{
		ListenAddr:      "127.0.0.1:0",
		DestinationAddr: pipeServer.Addr().String(),
		Password:        "123123",
	})
	require.NoError(t, err)

	// Start the pipe client, it's ready to accept new connections.
	err = pipeClient.Start()
	require.NoError(t, err)
	defer func() {
		require.NoError(t, pipeServer.Shutdown(context.Background()))
	}()

	// Connect to the pipe.
	pipeConn, err := net.Dial("udp", pipeClient.Addr().String())
	require.NoError(t, err)

	for i := 0; i < 1000; i++ {
		strMsg := fmt.Sprintf("test message %d: %s", i, strings.Repeat("a", i))
		msg := []byte(strMsg)

		// Write a message to the pipe.
		_, err = pipeConn.Write(msg)
		require.NoError(t, err)

		// Now read the response from the echo server.
		buf := make([]byte, len(msg))
		_, err = io.ReadFull(pipeConn, buf)
		require.NoError(t, err)

		// Check that the echo pipe response was received correctly.
		require.Equal(t, msg, buf)

		// Now check that the echo pipe received the message correctly.
		udpMsg := udpSrv.ReceivedMsg(i)
		require.NotNil(t, udpMsg)
		require.Equal(t, msg, udpMsg)
	}
}

func TestServer_Start_probeDetection(t *testing.T) {
	// Start the echo server where the pipe will proxy data.
	udpSrv := &testutil.UDPEchoServer{}
	err := udpSrv.Start()
	require.NoError(t, err)
	defer log.OnCloserError(udpSrv, log.DEBUG)

	// The server where pipeServer will proxy probes.
	rewriteListen, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	defer log.OnCloserError(rewriteListen, log.DEBUG)

	rewriteServer := &http.Server{
		Handler: http.HandlerFunc(func(rw http.ResponseWriter, r *http.Request) {
			rw.WriteHeader(http.StatusOK)
			_, _ = rw.Write([]byte(r.URL.String()))
		}),
	}
	go func() {
		_ = rewriteServer.Serve(rewriteListen)
	}()

	// Create the pipe server proxying data to that UDP echo server.
	pipeServer, err := pipe.NewServer(&pipe.Config{
		ListenAddr:           "127.0.0.1:0",
		DestinationAddr:      udpSrv.Addr(),
		Password:             "123123",
		ServerMode:           true,
		ProbeReverseProxyURL: fmt.Sprintf("http://%s", rewriteListen.Addr()),
	})
	require.NoError(t, err)

	// Start the pipe server, it's ready to accept new connections.
	err = pipeServer.Start()
	require.NoError(t, err)
	defer func() {
		require.NoError(t, pipeServer.Shutdown(context.Background()))
	}()

	// Connect to the pipe server.
	pipeConn, err := tls.Dial("tcp", pipeServer.Addr().String(), &tls.Config{InsecureSkipVerify: true})
	require.NoError(t, err)
	defer log.OnCloserError(pipeConn, log.DEBUG)

	_ = pipeConn.SetDeadline(time.Now().Add(time.Second * 1))

	// Create a probe request.
	r, err := http.NewRequest(http.MethodGet, "https://example.com/probe", nil)
	require.NoError(t, err)

	// Send the probe request to the server.
	err = r.Write(pipeConn)
	require.NoError(t, err)

	// Read what the server responded with to the probe.
	br := bufio.NewReader(pipeConn)
	resp, err := http.ReadResponse(br, nil)
	require.NoError(t, err)

	// Check that the response is the same as the reverse proxy has written.
	require.Equal(t, http.StatusOK, resp.StatusCode)

	responseBytes, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, "/probe", string(responseBytes))
}
