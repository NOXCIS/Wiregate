package testutil

import (
	"errors"
	"io"
	"net"
	"sync"

	"github.com/ameshkov/udptlspipe/internal/udp"
)

// UDPEchoServer is a test UDP pipe that accepts incoming connections and saves
// the information that it has received.
type UDPEchoServer struct {
	listen   net.Listener
	received [][]byte

	mu sync.Mutex
}

// ReceivedMsg returns the message received with the specified number of nil
// if there are no. Messages numbers start with 0.
func (s *UDPEchoServer) ReceivedMsg(num int) (b []byte) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if len(s.received) <= num {
		return nil
	}

	return s.received[num]
}

// Addr returns the address the pipe listens to.
func (s *UDPEchoServer) Addr() (str string) {
	if s.listen == nil {
		return ""
	}

	return s.listen.Addr().String()
}

// Start starts the echo pipe.
func (s *UDPEchoServer) Start() (err error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.listen != nil {
		return errors.New("pipe is already started")
	}

	s.listen, err = udp.Listen("udp", "127.0.0.1:0")

	if err != nil {
		return err
	}

	go s.serve()

	return nil
}

// type check
var _ io.Closer = (*UDPEchoServer)(nil)

// Close implements the io.Closer interface for *UDPEchoServer.
func (s *UDPEchoServer) Close() (err error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	return s.listen.Close()
}

// serve implements the serving loop.
func (s *UDPEchoServer) serve() {
	for {
		conn, err := s.listen.Accept()
		if err != nil {
			// For simplicity, stop the pipe here.
			return
		}

		go s.serveConn(conn)
	}
}

// serveConn handles one connection.
func (s *UDPEchoServer) serveConn(conn net.Conn) {
	buf := make([]byte, 65536)

	for {
		n, err := conn.Read(buf)
		if err != nil {
			return
		}

		msg := make([]byte, n)
		copy(msg, buf[:n])

		s.mu.Lock()
		s.received = append(s.received, msg)
		s.mu.Unlock()

		_, _ = conn.Write(msg)
	}
}
