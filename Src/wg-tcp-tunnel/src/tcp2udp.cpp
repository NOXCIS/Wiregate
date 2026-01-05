// wg-tcp-tunnel - tcp2udp.cpp
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#include "tcp2udp.h"

#include <array>
#include <cstddef>
#include <functional>
#include <memory>

#include <boost/asio.hpp>
#include <boost/log/trivial.hpp>

#include "utils.hpp"

namespace wg::tunnel {

namespace asio = boost::asio;
#if ENABLE_TLS
namespace ssl = asio::ssl;
#endif
#if ENABLE_WEBSOCKET
namespace beast = boost::beast;
namespace ws = beast::websocket;
#endif
using namespace std::placeholders;
#define LOG(lvl) BOOST_LOG_TRIVIAL(lvl) << "tcp2udp::"

auto tcp2udp::run(utils::transport transport) -> void {
	LOG(info) << "run: " << utils::to_string(m_ep_tcp_acc) << " >> "
	          << utils::to_string(m_ep_udp_dest);
	m_transport = transport;
#if ENABLE_TLS
	if (m_transport == utils::transport::tls || m_transport == utils::transport::wss) {
		if (!init_ssl_context()) {
			LOG(error) << "run: Failed to initialize SSL context";
			return;
		}
		LOG(info) << "run: TLS enabled";
	}
#endif
	do_accept();
}

#if ENABLE_TLS
auto tcp2udp::init_ssl_context() -> bool {
	try {
		// Try to use TLS 1.3 if available, otherwise fallback to TLS 1.2
		// Use tls_server (negotiation) to allow TLS 1.3 preferred with TLS 1.2 fallback
		bool tls13_available = false;
		
		// Check if TLS 1.3 is available (OpenSSL 1.1.1+)
		#if defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10101000L
			// OpenSSL 1.1.1+ supports TLS 1.3
			// Use tls_server which allows negotiation: will try TLS 1.3 first, fallback to TLS 1.2
			// This is better than tlsv13_server which forces TLS 1.3 only
			m_ssl_ctx = std::make_unique<ssl::context>(ssl::context::tls_server);
			tls13_available = true;
			LOG(info) << "init_ssl_context: Using TLS server (TLS 1.3 preferred, TLS 1.2 fallback enabled)";
		#else
			// OpenSSL version is too old for TLS 1.3, use TLS 1.2
		m_ssl_ctx = std::make_unique<ssl::context>(ssl::context::tlsv12_server);
			LOG(info) << "init_ssl_context: Using TLS 1.2 (OpenSSL version < 1.1.1, TLS 1.3 not available)";
		#endif
		
		// Set TLS options - disable insecure protocols
		// When TLS 1.3 is available, prefer it but allow TLS 1.2 fallback for compatibility
		if (tls13_available) {
			// For TLS 1.3, disable older versions but allow TLS 1.2 as fallback
			// This allows negotiation: try TLS 1.3 first, fallback to TLS 1.2 if client doesn't support it
			m_ssl_ctx->set_options(
				ssl::context::default_workarounds |
				ssl::context::no_sslv2 |
				ssl::context::no_sslv3 |
				ssl::context::no_tlsv1 |
				ssl::context::no_tlsv1_1 |
				ssl::context::single_dh_use);
			// Note: We don't disable TLS 1.2 here to allow fallback if client doesn't support TLS 1.3
		} else {
			// For TLS 1.2, disable older versions but allow TLS 1.2
		m_ssl_ctx->set_options(
			ssl::context::default_workarounds |
			ssl::context::no_sslv2 |
			ssl::context::no_sslv3 |
			ssl::context::no_tlsv1 |
			ssl::context::no_tlsv1_1 |
			ssl::context::single_dh_use);
		}
		
		// Load server certificate
		if (!m_tls_config.cert_path.empty()) {
			m_ssl_ctx->use_certificate_chain_file(m_tls_config.cert_path);
			LOG(debug) << "init_ssl_context: Loaded certificate from " << m_tls_config.cert_path;
		}
		
		// Load server private key
		if (!m_tls_config.key_path.empty()) {
			m_ssl_ctx->use_private_key_file(m_tls_config.key_path, ssl::context::pem);
			LOG(debug) << "init_ssl_context: Loaded private key from " << m_tls_config.key_path;
		}
		
		// Load CA certificate for client verification (optional)
		if (!m_tls_config.ca_path.empty()) {
			m_ssl_ctx->load_verify_file(m_tls_config.ca_path);
			m_ssl_ctx->set_verify_mode(ssl::verify_peer);
			LOG(debug) << "init_ssl_context: Loaded CA certificate from " << m_tls_config.ca_path;
		}
		
		return true;
	} catch (const std::exception & e) {
		LOG(error) << "init_ssl_context: " << e.what();
		return false;
	}
}
#endif

auto tcp2udp::do_accept() -> void {
	auto socket = std::make_shared<asio::ip::tcp::socket>(m_io_context);
	m_tcp_acceptor.async_accept(m_io_context, [this](const auto & ec, auto && peer) {
		do_accept_handler(ec, std::forward<decltype(peer)>(peer));
	});
}

auto tcp2udp::do_accept_handler(const boost::system::error_code & ec, asio::ip::tcp::socket peer)
    -> void {
	if (ec) {
		LOG(error) << "accept [" << utils::to_string(m_ep_tcp_acc) << "]: " << ec.message();
	} else {
		LOG(debug) << "accept [" << utils::to_string(m_ep_tcp_acc)
		           << "]: New connection: peer=" << utils::to_string(peer.remote_endpoint());
		if (m_tcp_keep_alive_idle_time > 0) {
			// Setup TCP keep-alive on the session socket
			LOG(debug) << "tcp-keepalive [" << utils::to_string(peer.remote_endpoint())
			           << "]: idle=" << m_tcp_keep_alive_idle_time;
			utils::socket_set_keep_alive_idle(peer, m_tcp_keep_alive_idle_time);
			peer.set_option(asio::socket_base::keep_alive(true));
			peer.set_option(asio::socket_base::linger(true, 0));
		}
		// Start handling TCP packets
		switch (m_transport) {
		case utils::transport::raw:
			std::make_shared<tcp::session_raw>(*this, std::move(peer))->run();
			break;
#if ENABLE_TLS
		case utils::transport::tls:
			std::make_shared<tcp::session_tls>(*this, std::move(peer), *m_ssl_ctx)->run();
			break;
#if ENABLE_WEBSOCKET
		case utils::transport::wss:
			std::make_shared<tcp::session_wss>(*this, std::move(peer), *m_ssl_ctx)->run();
			break;
#endif
#endif
#if ENABLE_WEBSOCKET
		case utils::transport::websocket:
			std::make_shared<tcp::session_ws>(*this, std::move(peer))->run();
			break;
#endif
		}
	}
	// Handle next TCP connection
	do_accept();
}

auto tcp2udp::tcp::session_raw::run() -> void {
	LOG(info) << "session-raw::run: " << to_string();
	// Start handling TCP packets
	do_send_init();
}

auto tcp2udp::tcp::session_raw::do_send_init() -> void {
	do_send(sizeof(utils::ip::udp::header), true);
}

auto tcp2udp::tcp::session_raw::do_send(size_t rlen, bool ctrl) -> void {
	m_buffer_send.consume(m_buffer_send.size()); // Clean any previous data
	asio::async_read(m_socket, m_buffer_send, asio::transfer_exactly(rlen),
	                 [self = shared_from_this(), ctrl](const auto & ec, size_t length) {
		                 self->do_send_handler(ec, length, ctrl);
	                 });
}

auto tcp2udp::tcp::session_raw::do_send_handler(const boost::system::error_code & ec,
                                                size_t length, bool ctrl) -> void {

	if (ec) {
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "session-raw::send: Connection closed: peer="
			           << utils::to_string(m_socket_ep_remote);
			// Stop UDP receiver if there is no TCP session
			m_socket_udp_dest.cancel();
			return;
		}
		LOG(error) << "session-raw::send [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_send_init();
		return;
	}

	LOG(trace) << "session-raw::send [" << to_string(true) << "]: len=" << length;

	if (ctrl) {
		auto header =
		    reinterpret_cast<const utils::ip::udp::header *>(m_buffer_send.data().data());
		if (!header->valid()) {
			LOG(warning) << "session-raw::send [" << to_string() << "]: Invalid UDP header";
			// Handle next TCP packet
			do_send_init();
			return;
		}
		// Check if the packet is a control packet
		if (header->m_length == 0) {
			// Handle next TCP packet
			do_send_init();
			return;
		}
		// Handle UDP packet payload
		do_send(header->m_length);
		return;
	}

	// At this point we know that the control header was valid
	if (!std::exchange(m_initialized, true)) {
		// Start handling UDP packets
		do_recv();
	}

	// Copy data to persistent buffer for async send
	auto data = m_buffer_send.data();
	m_buffer_udp_send_length = asio::buffer_size(data);
	asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
	m_socket_udp_dest.async_send(
	    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length),
	    [self = shared_from_this()](const auto & ec, size_t length) {
		    self->do_udp_send_handler(ec, length);
	    });
}

auto tcp2udp::tcp::session_raw::do_udp_send_handler(const boost::system::error_code & ec,
                                                    size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-raw::udp-send [" << to_string() << "]: " << ec.message();
	} else {
		LOG(trace) << "session-raw::udp-send [" << to_string() << "]: len=" << length;
	}

	// Handle next TCP packet
	do_send_init();
}

auto tcp2udp::tcp::session_raw::do_recv() -> void {
	m_socket_udp_dest.async_receive(asio::buffer(m_buffer_recv),
	                                [self = shared_from_this()](const auto & ec, size_t length) {
		                                self->do_recv_handler(ec, length);
	                                });
}

auto tcp2udp::tcp::session_raw::do_recv_handler(const boost::system::error_code & ec,
                                                size_t length) -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-raw::recv [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_recv();
		return;
	}

	LOG(trace) << "session-raw::recv [" << to_string(true) << "]: len=" << length;
	// Send payload with attached UDP header asynchronously
	m_tcp_recv_length = length;
	m_tcp_send_header = utils::ip::udp::header(m_socket_udp_dest.remote_endpoint().port(),
	                              m_socket_udp_dest.local_endpoint().port(),
	                              static_cast<uint16_t>(length));
	const std::array<asio::const_buffer, 2> iovec{ asio::buffer(&m_tcp_send_header, sizeof(m_tcp_send_header)),
		                                           asio::buffer(m_buffer_recv, m_tcp_recv_length) };
	asio::async_write(m_socket, iovec,
	                  [self = shared_from_this()](const auto & ec, size_t length) {
		                  self->do_tcp_send_handler(ec, length);
	                  });
}

auto tcp2udp::tcp::session_raw::do_tcp_send_handler(const boost::system::error_code & ec,
                                                    size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-raw::tcp-send [" << to_string() << "]: " << ec.message();
		// Connection failed - cancel UDP receiver
		m_socket_udp_dest.cancel();
		return;
	}

	LOG(trace) << "session-raw::tcp-send [" << to_string() << "]: len=" << length;

	// Handle next UDP packet
	do_recv();
}

#if ENABLE_WEBSOCKET

auto tcp2udp::tcp::session_ws::run() -> void {
	LOG(info) << "session-ws::run: " << to_string();
	// Ensure that the WebSocket stream will be binary
	m_ws.binary(true);
	// Start handling WebSocket handshake
	do_accept();
}

auto tcp2udp::tcp::session_ws::do_accept() -> void {
	// Set suggested timeout settings for the WebSocket server
	m_ws.set_option(ws::stream_base::timeout::suggested(beast::role_type::server));
	// Modify the server handshake response headers
	m_ws.set_option(ws::stream_base::decorator([&](ws::response_type & res) {
		LOG(debug) << "session-ws::accept: Sending response: peer="
		           << utils::to_string(m_socket_ep_remote);
		for (const auto & [key, value] : m_ws_headers)
			res.insert(key, value);
	}));
	m_ws.async_accept(
	    [self = shared_from_this()](const auto & ec) { self->do_accept_handler(ec); });
}

auto tcp2udp::tcp::session_ws::do_accept_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "session-ws::accept [" << to_string() << "]: " << ec.message();
		return;
	}
	LOG(debug) << "session-ws::accept: Handshake accepted: peer="
	           << utils::to_string(m_socket_ep_remote);
	// Start handling WebSocket packets
	do_send();
	// Start handling UDP packets
	do_recv();
}

auto tcp2udp::tcp::session_ws::do_send() -> void {
	m_buffer_send.clear();
	m_ws.async_read(m_buffer_send, [self = shared_from_this()](const auto & ec, size_t length) {
		self->do_send_handler(ec, length);
	});
}

auto tcp2udp::tcp::session_ws::do_send_handler(const boost::system::error_code & ec, size_t length)
    -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "session-ws::send: Connection closed: peer="
			           << utils::to_string(m_socket_ep_remote);
			// Stop UDP receiver if there is no TCP session
			m_socket_udp_dest.cancel();
			return;
		}
		LOG(error) << "session-ws::send [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_send();
		return;
	}

		LOG(trace) << "session-ws::send [" << to_string(true) << "]: len=" << length;

	// Copy data to persistent buffer for async send
	auto data = m_buffer_send.data();
	m_buffer_udp_send_length = asio::buffer_size(data);
	asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
	m_socket_udp_dest.async_send(
	    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length),
	    [self = shared_from_this()](const auto & ec, size_t length) {
		    self->do_udp_send_handler(ec, length);
	    });
}

auto tcp2udp::tcp::session_ws::do_udp_send_handler(const boost::system::error_code & ec,
                                                   size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-ws::udp-send [" << to_string() << "]: " << ec.message();
	} else {
		LOG(trace) << "session-ws::udp-send [" << to_string() << "]: len=" << length;
	}

	// Handle next WebSocket packet
	do_send();
}

auto tcp2udp::tcp::session_ws::do_recv() -> void {
	m_socket_udp_dest.async_receive(asio::buffer(m_buffer_recv),
	                                [self = shared_from_this()](const auto & ec, size_t length) {
		                                self->do_recv_handler(ec, length);
	                                });
}

auto tcp2udp::tcp::session_ws::do_recv_handler(const boost::system::error_code & ec, size_t length)
    -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-ws::recv [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_recv();
		return;
	}

	LOG(trace) << "session-ws::recv [" << to_string(true) << "]: len=" << length;
	m_ws_recv_length = length;
	m_ws.async_write(asio::buffer(m_buffer_recv, m_ws_recv_length),
	                 [self = shared_from_this()](const auto & ec, size_t length) {
		                 self->do_ws_send_handler(ec, length);
	                 });
}

auto tcp2udp::tcp::session_ws::do_ws_send_handler(const boost::system::error_code & ec,
                                                  size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-ws::ws-send [" << to_string() << "]: " << ec.message();
		// Connection failed - cancel UDP receiver
		m_socket_udp_dest.cancel();
		return;
	}

	LOG(trace) << "session-ws::ws-send [" << to_string() << "]: len=" << length;

	// Handle next UDP packet
	do_recv();
}

#endif

auto tcp2udp::tcp::session::to_string(bool verbose) -> std::string {
	std::string str = utils::to_string(m_socket_ep_remote);
	if (verbose)
		str += " -> " + utils::to_string(m_socket.local_endpoint());
	str += " >> ";
	if (verbose)
		str += utils::to_string(m_socket_udp_dest.local_endpoint()) + " -> ";
	str += utils::to_string(m_socket_udp_dest.remote_endpoint());
	return str;
}

#if ENABLE_TLS

// ============================================================================
// TLS Session Implementation
// ============================================================================

auto tcp2udp::tcp::session_tls::run() -> void {
	LOG(info) << "session-tls::run: " << to_string();
	// Start TLS handshake
	do_handshake();
}

auto tcp2udp::tcp::session_tls::to_string(bool verbose) -> std::string {
	std::string str = "tls:" + m_socket_ep_remote.address().to_string() + ":" +
	                  std::to_string(m_socket_ep_remote.port());
	if (verbose)
		str += " -> tls:" + m_ssl_stream.lowest_layer().local_endpoint().address().to_string() +
		       ":" + std::to_string(m_ssl_stream.lowest_layer().local_endpoint().port());
	str += " >> ";
	if (verbose)
		str += utils::to_string(m_socket_udp_dest.local_endpoint()) + " -> ";
	str += utils::to_string(m_socket_udp_dest.remote_endpoint());
	return str;
}

auto tcp2udp::tcp::session_tls::do_handshake() -> void {
	m_ssl_stream.async_handshake(ssl::stream_base::server,
	    [self = shared_from_this()](const auto & ec) {
		    self->do_handshake_handler(ec);
	    });
}

auto tcp2udp::tcp::session_tls::do_handshake_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "session-tls::handshake [" << to_string() << "]: " << ec.message();
		return;
	}
	LOG(debug) << "session-tls::handshake: TLS handshake complete: peer="
	           << utils::to_string(m_socket_ep_remote);
	// Start handling TLS packets
	do_send_init();
}

auto tcp2udp::tcp::session_tls::do_send_init() -> void {
	do_send(sizeof(utils::ip::udp::header), true);
}

auto tcp2udp::tcp::session_tls::do_send(size_t rlen, bool ctrl) -> void {
	m_buffer_send.consume(m_buffer_send.size());
	asio::async_read(m_ssl_stream, m_buffer_send, asio::transfer_exactly(rlen),
	                 [self = shared_from_this(), ctrl](const auto & ec, size_t length) {
		                 self->do_send_handler(ec, length, ctrl);
	                 });
}

auto tcp2udp::tcp::session_tls::do_send_handler(const boost::system::error_code & ec,
                                                size_t length, bool ctrl) -> void {
	if (ec) {
		if (ec == asio::error::eof || ec == asio::error::connection_reset ||
		    ec == asio::ssl::error::stream_truncated) {
			LOG(debug) << "session-tls::send: Connection closed: peer="
			           << utils::to_string(m_socket_ep_remote);
			m_socket_udp_dest.cancel();
			return;
		}
		LOG(error) << "session-tls::send [" << to_string() << "]: " << ec.message();
		do_send_init();
		return;
	}

	LOG(trace) << "session-tls::send [" << to_string(true) << "]: len=" << length;

	if (ctrl) {
		auto header =
		    reinterpret_cast<const utils::ip::udp::header *>(m_buffer_send.data().data());
		if (!header->valid()) {
			LOG(warning) << "session-tls::send [" << to_string() << "]: Invalid UDP header";
			do_send_init();
			return;
		}
		if (header->m_length == 0) {
			do_send_init();
			return;
		}
		do_send(header->m_length);
		return;
	}

	if (!std::exchange(m_initialized, true)) {
		do_recv();
	}

	auto data = m_buffer_send.data();
	m_buffer_udp_send_length = asio::buffer_size(data);
	asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
	m_socket_udp_dest.async_send(
	    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length),
	    [self = shared_from_this()](const auto & ec, size_t length) {
		    self->do_udp_send_handler(ec, length);
	    });
}

auto tcp2udp::tcp::session_tls::do_udp_send_handler(const boost::system::error_code & ec,
                                                    size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-tls::udp-send [" << to_string() << "]: " << ec.message();
	} else {
		LOG(trace) << "session-tls::udp-send [" << to_string() << "]: len=" << length;
	}
	do_send_init();
}

auto tcp2udp::tcp::session_tls::do_recv() -> void {
	m_socket_udp_dest.async_receive(asio::buffer(m_buffer_recv),
	                                [self = shared_from_this()](const auto & ec, size_t length) {
		                                self->do_recv_handler(ec, length);
	                                });
}

auto tcp2udp::tcp::session_tls::do_recv_handler(const boost::system::error_code & ec,
                                                size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-tls::recv [" << to_string() << "]: " << ec.message();
		do_recv();
		return;
	}

	LOG(trace) << "session-tls::recv [" << to_string(true) << "]: len=" << length;
	m_tcp_recv_length = length;
	m_tcp_send_header = utils::ip::udp::header(m_socket_udp_dest.remote_endpoint().port(),
	                              m_socket_udp_dest.local_endpoint().port(),
	                              static_cast<uint16_t>(length));
	const std::array<asio::const_buffer, 2> iovec{ asio::buffer(&m_tcp_send_header, sizeof(m_tcp_send_header)),
		                                           asio::buffer(m_buffer_recv, m_tcp_recv_length) };
	asio::async_write(m_ssl_stream, iovec,
	                  [self = shared_from_this()](const auto & ec, size_t length) {
		                  self->do_tls_send_handler(ec, length);
	                  });
}

auto tcp2udp::tcp::session_tls::do_tls_send_handler(const boost::system::error_code & ec,
                                                    size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-tls::tls-send [" << to_string() << "]: " << ec.message();
		m_socket_udp_dest.cancel();
		return;
	}

	LOG(trace) << "session-tls::tls-send [" << to_string() << "]: len=" << length;
	do_recv();
}

#if ENABLE_WEBSOCKET

// ============================================================================
// WSS (WebSocket over TLS) Session Implementation
// ============================================================================

auto tcp2udp::tcp::session_wss::run() -> void {
	LOG(info) << "session-wss::run: " << to_string();
	// Start TLS handshake first
	do_tls_handshake();
}

auto tcp2udp::tcp::session_wss::to_string(bool verbose) -> std::string {
	std::string str = "wss:" + m_socket_ep_remote.address().to_string() + ":" +
	                  std::to_string(m_socket_ep_remote.port());
	if (verbose)
		str += " -> wss:" + m_ssl_stream.lowest_layer().local_endpoint().address().to_string() +
		       ":" + std::to_string(m_ssl_stream.lowest_layer().local_endpoint().port());
	str += " >> ";
	if (verbose)
		str += utils::to_string(m_socket_udp_dest.local_endpoint()) + " -> ";
	str += utils::to_string(m_socket_udp_dest.remote_endpoint());
	return str;
}

auto tcp2udp::tcp::session_wss::do_tls_handshake() -> void {
	m_ssl_stream.async_handshake(ssl::stream_base::server,
	    [self = shared_from_this()](const auto & ec) {
		    self->do_tls_handshake_handler(ec);
	    });
}

auto tcp2udp::tcp::session_wss::do_tls_handshake_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "session-wss::tls-handshake [" << to_string() << "]: " << ec.message();
		return;
	}
	LOG(debug) << "session-wss::tls-handshake: TLS handshake complete: peer="
	           << utils::to_string(m_socket_ep_remote);
	// Now perform WebSocket handshake
	m_ws.binary(true);
	do_accept();
}

auto tcp2udp::tcp::session_wss::do_accept() -> void {
	m_ws.set_option(ws::stream_base::timeout::suggested(beast::role_type::server));
	m_ws.set_option(ws::stream_base::decorator([&](ws::response_type & res) {
		LOG(debug) << "session-wss::accept: Sending response: peer="
		           << utils::to_string(m_socket_ep_remote);
		for (const auto & [key, value] : m_ws_headers)
			res.insert(key, value);
	}));
	m_ws.async_accept(
	    [self = shared_from_this()](const auto & ec) { self->do_accept_handler(ec); });
}

auto tcp2udp::tcp::session_wss::do_accept_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "session-wss::accept [" << to_string() << "]: " << ec.message();
		return;
	}
	LOG(debug) << "session-wss::accept: WebSocket handshake accepted: peer="
	           << utils::to_string(m_socket_ep_remote);
	do_send();
	do_recv();
}

auto tcp2udp::tcp::session_wss::do_send() -> void {
	m_buffer_send.clear();
	m_ws.async_read(m_buffer_send, [self = shared_from_this()](const auto & ec, size_t length) {
		self->do_send_handler(ec, length);
	});
}

auto tcp2udp::tcp::session_wss::do_send_handler(const boost::system::error_code & ec, size_t length)
    -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset ||
		    ec == asio::ssl::error::stream_truncated) {
			LOG(debug) << "session-wss::send: Connection closed: peer="
			           << utils::to_string(m_socket_ep_remote);
			m_socket_udp_dest.cancel();
			return;
		}
		LOG(error) << "session-wss::send [" << to_string() << "]: " << ec.message();
		do_send();
		return;
	}

	LOG(trace) << "session-wss::send [" << to_string(true) << "]: len=" << length;

	auto data = m_buffer_send.data();
	m_buffer_udp_send_length = asio::buffer_size(data);
	asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
	m_socket_udp_dest.async_send(
	    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length),
	    [self = shared_from_this()](const auto & ec, size_t length) {
		    self->do_udp_send_handler(ec, length);
	    });
}

auto tcp2udp::tcp::session_wss::do_udp_send_handler(const boost::system::error_code & ec,
                                                    size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-wss::udp-send [" << to_string() << "]: " << ec.message();
	} else {
		LOG(trace) << "session-wss::udp-send [" << to_string() << "]: len=" << length;
	}
	do_send();
}

auto tcp2udp::tcp::session_wss::do_recv() -> void {
	m_socket_udp_dest.async_receive(asio::buffer(m_buffer_recv),
	                                [self = shared_from_this()](const auto & ec, size_t length) {
		                                self->do_recv_handler(ec, length);
	                                });
}

auto tcp2udp::tcp::session_wss::do_recv_handler(const boost::system::error_code & ec, size_t length)
    -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-wss::recv [" << to_string() << "]: " << ec.message();
		do_recv();
		return;
	}

	LOG(trace) << "session-wss::recv [" << to_string(true) << "]: len=" << length;
	m_ws_recv_length = length;
	m_ws.async_write(asio::buffer(m_buffer_recv, m_ws_recv_length),
	                 [self = shared_from_this()](const auto & ec, size_t length) {
		                 self->do_ws_send_handler(ec, length);
	                 });
}

auto tcp2udp::tcp::session_wss::do_ws_send_handler(const boost::system::error_code & ec,
                                                   size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "session-wss::ws-send [" << to_string() << "]: " << ec.message();
		m_socket_udp_dest.cancel();
		return;
	}

	LOG(trace) << "session-wss::ws-send [" << to_string() << "]: len=" << length;
	do_recv();
}

#endif // ENABLE_WEBSOCKET
#endif // ENABLE_TLS

}; // namespace wg::tunnel
