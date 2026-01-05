// wg-tcp-tunnel - udp2tcp.cpp
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#include "udp2tcp.h"

#include <array>
#include <chrono>
#include <functional>
#include <memory>
#include <regex>
#include <stdexcept>
#include <string>

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
#define LOG(lvl) BOOST_LOG_TRIVIAL(lvl) << "udp2tcp::"

auto udp2tcp::run(utils::transport transport) -> void {
	m_ep_tcp_dest_cache = asio::ip::tcp::endpoint();
	LOG(info) << "run: " << utils::to_string(m_ep_udp_acc) << " >> "
	          << utils::to_string(m_ep_tcp_dest_cache);
	m_transport = transport;
	
	// Configure UDP socket receive buffer to handle high packet rates
	// Default is often ~200KB, increase to 1MB to reduce packet drops
	try {
		asio::socket_base::receive_buffer_size option(1024 * 1024); // 1MB
		m_socket_udp_acc.set_option(option);
		LOG(debug) << "UDP receive buffer set to 1MB";
	} catch (const std::exception & e) {
		LOG(warning) << "Failed to set UDP receive buffer size: " << e.what();
	}

#if ENABLE_TLS
	if (m_transport == utils::transport::tls || m_transport == utils::transport::wss) {
		if (!init_ssl_context()) {
			LOG(error) << "run: Failed to initialize SSL context";
			return;
		}
		LOG(info) << "run: TLS enabled";
	}
#endif
	
#if ENABLE_WEBSOCKET
	// Ensure that the WebSocket stream will be binary
	m_ws.binary(true);
#endif

	// Start connection cleanup timer
	do_cleanup_init();
	
	do_send();
}

#if ENABLE_TLS
auto udp2tcp::init_ssl_context() -> bool {
	try {
		// Try to use TLS 1.3 if available, otherwise fallback to TLS 1.2
		// Use tls_client (negotiation) to allow TLS 1.3 preferred with TLS 1.2 fallback
		bool tls13_available = false;
		
		// Check if TLS 1.3 is available (OpenSSL 1.1.1+)
		#if defined(OPENSSL_VERSION_NUMBER) && OPENSSL_VERSION_NUMBER >= 0x10101000L
			// OpenSSL 1.1.1+ supports TLS 1.3
			// Use tls_client which allows negotiation: will try TLS 1.3 first, fallback to TLS 1.2
			// This is better than tlsv13_client which forces TLS 1.3 only
			m_ssl_ctx = std::make_unique<ssl::context>(ssl::context::tls_client);
			tls13_available = true;
			LOG(info) << "init_ssl_context: Using TLS client (TLS 1.3 preferred, TLS 1.2 fallback enabled)";
		#else
			// OpenSSL version is too old for TLS 1.3, use TLS 1.2
		m_ssl_ctx = std::make_unique<ssl::context>(ssl::context::tlsv12_client);
			LOG(info) << "init_ssl_context: Using TLS 1.2 (OpenSSL version < 1.1.1, TLS 1.3 not available)";
		#endif
		
		// Set TLS options - disable insecure protocols
		// When TLS 1.3 is available, prefer it but allow TLS 1.2 fallback for compatibility
		if (tls13_available) {
			// For TLS 1.3, disable older versions but allow TLS 1.2 as fallback
			// This allows negotiation: try TLS 1.3 first, fallback to TLS 1.2 if server doesn't support it
		m_ssl_ctx->set_options(
			ssl::context::default_workarounds |
			ssl::context::no_sslv2 |
			ssl::context::no_sslv3 |
			ssl::context::no_tlsv1 |
			ssl::context::no_tlsv1_1);
			// Note: We don't disable TLS 1.2 here to allow fallback if server doesn't support TLS 1.3
		} else {
			// For TLS 1.2, disable older versions but allow TLS 1.2
			m_ssl_ctx->set_options(
				ssl::context::default_workarounds |
				ssl::context::no_sslv2 |
				ssl::context::no_sslv3 |
				ssl::context::no_tlsv1 |
				ssl::context::no_tlsv1_1);
		}
		
		// Configure certificate verification
		if (m_tls_config.skip_verification) {
			LOG(warning) << "init_ssl_context: Certificate verification disabled (insecure)";
			m_ssl_ctx->set_verify_mode(ssl::verify_none);
		} else if (m_tls_config.allow_self_signed) {
			LOG(info) << "init_ssl_context: Allowing self-signed certificates";
			m_ssl_ctx->set_verify_mode(ssl::verify_peer);
			m_ssl_ctx->set_verify_callback([](bool preverified, ssl::verify_context& ctx) {
				// Allow self-signed certificates
				return true;
			});
		} else if (m_tls_config.verify) {
			m_ssl_ctx->set_verify_mode(ssl::verify_peer);
			// Load default CA certificates
			m_ssl_ctx->set_default_verify_paths();
			if (!m_tls_config.ca_path.empty()) {
				m_ssl_ctx->load_verify_file(m_tls_config.ca_path);
				LOG(debug) << "init_ssl_context: Loaded CA certificate from " << m_tls_config.ca_path;
			}
		}
		
		return true;
	} catch (const std::exception & e) {
		LOG(error) << "init_ssl_context: " << e.what();
		return false;
	}
}
#endif

auto udp2tcp::to_string(bool verbose) -> std::string {
	std::string str = utils::to_string(m_ep_udp_sender);
	if (verbose)
		str += " -> " + utils::to_string(m_ep_udp_acc);
	str += " >> ";
	if (verbose)
		str += utils::to_string(m_socket_tcp_dest.local_endpoint()) + " -> ";
	str += utils::to_string(m_socket_tcp_dest.remote_endpoint());
	return str;
}

auto udp2tcp::do_connect() -> void {
	try {
		m_ep_tcp_dest_cache = m_ep_tcp_dest_provider.tcp_dest_ep();
		// Ensure the socket is in a clean state before connecting
		if (m_socket_tcp_dest.is_open()) {
			m_socket_tcp_dest.close();
		}
		// Open the socket with the correct protocol family
		m_socket_tcp_dest.open(m_ep_tcp_dest_cache.protocol());
		LOG(debug) << "connect: Connecting to " << utils::to_string(m_ep_tcp_dest_cache);
		m_socket_tcp_dest.async_connect(m_ep_tcp_dest_cache,
		                                [this](const auto & ec) { do_connect_handler(ec); });
	} catch (const std::exception & e) {
		LOG(error) << "connect: Get destination TCP endpoint: " << e.what();
		// Handle next UDP packet
		do_send();
	}
}

auto udp2tcp::do_connect_handler(const boost::system::error_code & ec) -> void {

	if (ec) {
		LOG(error) << "connect [" << utils::to_string(m_ep_tcp_dest_cache)
		           << "]: " << ec.message();
		m_socket_tcp_dest.close();
		// Handle next UDP packet
		do_send();
		return;
	}

	LOG(debug) << "connect: Connected: peer=" << utils::to_string(m_ep_tcp_dest_cache);

	if (m_tcp_keep_alive_idle_time > 0) {
		LOG(debug) << "tcp-keepalive [" << utils::to_string(m_socket_tcp_dest.remote_endpoint())
		           << "]: idle=" << m_tcp_keep_alive_idle_time;
		utils::socket_set_keep_alive_idle(m_socket_tcp_dest, m_tcp_keep_alive_idle_time);
		m_socket_tcp_dest.set_option(asio::socket_base::keep_alive(true));
		m_socket_tcp_dest.set_option(asio::socket_base::linger(true, 0));
	}

#if ENABLE_TLS
	if (m_transport == utils::transport::tls) {
		// Create SSL stream and perform TLS handshake
		m_ssl_stream = std::make_unique<ssl::stream<asio::ip::tcp::socket &>>(m_socket_tcp_dest, *m_ssl_ctx);
		LOG(debug) << "connect: TLS handshake: peer=" << utils::to_string(m_ep_tcp_dest_cache);
		m_ssl_stream->async_handshake(ssl::stream_base::client,
		                              [this](const auto & ec) { do_tls_handshake_handler(ec); });
		return;
	}
#if ENABLE_WEBSOCKET
	if (m_transport == utils::transport::wss) {
		// Create SSL stream and perform TLS handshake first
		m_ssl_stream = std::make_unique<ssl::stream<asio::ip::tcp::socket &>>(m_socket_tcp_dest, *m_ssl_ctx);
		LOG(debug) << "connect: TLS handshake for WSS: peer=" << utils::to_string(m_ep_tcp_dest_cache);
		m_ssl_stream->async_handshake(ssl::stream_base::client,
		                              [this](const auto & ec) { do_tls_handshake_handler(ec); });
		return;
	}
#endif
#endif

#if ENABLE_WEBSOCKET
	if (m_transport == utils::transport::websocket) {
		// Set suggested timeout settings for the websocket client
		m_ws.set_option(ws::stream_base::timeout::suggested(beast::role_type::client));
		// Modify the client handshake request headers
		m_ws.set_option(ws::stream_base::decorator([&](ws::request_type & req) {
			for (const auto & [key, value] : m_ws_headers)
				req.set(key, value);
		}));
		LOG(debug) << "connect: Handshake: peer=" << utils::to_string(m_ep_tcp_dest_cache);
		// Perform WebSocket handshake asynchronously. In order to override the hard-coded "Host"
		// header, user needs to provide the "Host" header via ws_headers() method.
		m_ws.async_handshake("example.com", "/",
		                     [this](const auto & ec) { do_ws_handshake_handler(ec); });
		return;
	}
#endif

	// Start handling application-level keep-alive
	do_app_keep_alive_init();
	// Start handling TCP packets
	do_recv_init();

	// Send UDP packet which was waiting for TCP connection
	// Next UDP packet will be received after this send completes
	m_tcp_send_in_progress = true;
	do_send_buffer();
}

#if ENABLE_TLS
auto udp2tcp::do_tls_handshake_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "tls-handshake [" << utils::to_string(m_ep_tcp_dest_cache)
		           << "]: " << ec.message();
		m_ssl_stream.reset();
		m_socket_tcp_dest.close();
		// Handle next UDP packet - will trigger reconnect
		do_send();
		return;
	}

	LOG(debug) << "tls-handshake: Completed: peer=" << utils::to_string(m_ep_tcp_dest_cache);

#if ENABLE_WEBSOCKET
	if (m_transport == utils::transport::wss) {
		// Now perform WebSocket handshake over TLS
		m_wss = std::make_unique<ws::stream<ssl::stream<asio::ip::tcp::socket &> &>>(*m_ssl_stream);
		m_wss->binary(true);
		m_wss->set_option(ws::stream_base::timeout::suggested(beast::role_type::client));
		m_wss->set_option(ws::stream_base::decorator([&](ws::request_type & req) {
			for (const auto & [key, value] : m_ws_headers)
				req.set(key, value);
		}));
		LOG(debug) << "tls-handshake: WSS handshake: peer=" << utils::to_string(m_ep_tcp_dest_cache);
		m_wss->async_handshake("example.com", "/",
		                       [this](const auto & ec) { do_ws_handshake_handler(ec); });
		return;
	}
#endif

	// TLS-only mode - start handling packets
	do_app_keep_alive_init();
	do_recv_init();
	m_tcp_send_in_progress = true;
	do_send_buffer();
}
#endif

#if ENABLE_WEBSOCKET
auto udp2tcp::do_ws_handshake_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "ws-handshake [" << utils::to_string(m_ep_tcp_dest_cache)
		           << "]: " << ec.message();
#if ENABLE_TLS
		if (m_transport == utils::transport::wss) {
			m_wss.reset();
			m_ssl_stream.reset();
		}
#endif
		m_socket_tcp_dest.close();
		// Handle next UDP packet - will trigger reconnect
		do_send();
		return;
	}

	LOG(debug) << "ws-handshake: Completed: peer=" << utils::to_string(m_ep_tcp_dest_cache);

	// Start handling application-level keep-alive
	do_app_keep_alive_init();
	// Start handling TCP packets
	do_recv_init();

	// Send UDP packet which was waiting for TCP connection
	// Next UDP packet will be received after this send completes
	m_tcp_send_in_progress = true;
	do_send_buffer();
}
#endif

auto udp2tcp::do_app_keep_alive_init() -> void {
	do_app_keep_alive(true);
}

auto udp2tcp::do_app_keep_alive(bool init) -> void {

	// This call is a no-op if keep-alive is disabled
	if (m_app_keep_alive_idle_time == 0)
		return;

	auto time = std::chrono::seconds(m_app_keep_alive_idle_time);
	// Set or update timer and check whether the previous handler was cancelled
	if (m_app_keep_alive_timer.expires_after(time) == 0 && !init)
		return;

	LOG(trace) << "app-keepalive [" << to_string() << "]: idle=" << m_app_keep_alive_idle_time;
	m_app_keep_alive_timer.async_wait([this](const auto & ec) { do_app_keep_alive_handler(ec); });
}

auto udp2tcp::do_app_keep_alive_handler(const boost::system::error_code & ec) -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "app-keepalive [" << to_string() << "]: " << ec.message();
		return;
	}

	if (!m_socket_tcp_dest.is_open())
		return;

	// Don't send keepalive if a data send is in progress (shared buffer)
	if (m_tcp_send_in_progress) {
		// Reschedule keepalive
		do_app_keep_alive_init();
		return;
	}

	LOG(debug) << "app-keepalive [" << to_string() << "]: Sending keep-alive packet";

	// Send a control packet asynchronously
	m_tcp_send_in_progress = true;
	m_tcp_send_header = utils::ip::udp::header(m_ep_udp_sender.port(), m_ep_udp_acc.port(), 0);
	asio::async_write(m_socket_tcp_dest, asio::buffer(&m_tcp_send_header, sizeof(m_tcp_send_header)),
	                  [this](const auto & ec, size_t length) { do_keepalive_send_handler(ec, length); });
}

auto udp2tcp::do_keepalive_send_handler(const boost::system::error_code & ec, size_t length) -> void {
	m_tcp_send_in_progress = false;

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "keepalive-send [" << to_string() << "]: " << ec.message();
		// Connection failed - close socket so next UDP packet triggers reconnect
		m_app_keep_alive_timer.cancel();
		m_socket_tcp_dest.close();
		// Resume UDP receiving
		do_send();
		return;
	}

	LOG(trace) << "keepalive-send [" << to_string() << "]: len=" << length;

	// Initialize next keep-alive timer
	do_app_keep_alive_init();

	// Resume UDP receiving (in case it was waiting)
	do_send();
}

auto udp2tcp::do_send() -> void {
	// Allow overlapping receives - async operations are thread-safe
	// This allows multiple UDP packets to be queued for TCP send
	m_socket_udp_acc.async_receive_from(
	    asio::buffer(m_buffer_send), m_ep_udp_sender,
	    [this](const auto & ec, size_t length) { do_send_handler(ec, length); });
}

auto udp2tcp::do_send_buffer() -> void {
	LOG(trace) << "send [" << to_string(true) << "]: len=" << m_buffer_send_length;
	switch (m_transport) {
	case utils::transport::raw: {
		// Send payload with attached UDP header asynchronously
		m_tcp_send_header = utils::ip::udp::header(m_ep_udp_sender.port(), m_ep_udp_acc.port(),
		                              static_cast<uint16_t>(m_buffer_send_length));
		const std::array<asio::const_buffer, 2> iovec{ asio::buffer(&m_tcp_send_header, sizeof(m_tcp_send_header)),
			                                           asio::buffer(m_buffer_send,
			                                                        m_buffer_send_length) };
		asio::async_write(m_socket_tcp_dest, iovec,
		                  [this](const auto & ec, size_t length) { do_send_buffer_handler(ec, length); });
	} break;
#if ENABLE_WEBSOCKET
	case utils::transport::websocket:
		m_ws.async_write(asio::buffer(m_buffer_send, m_buffer_send_length),
		                 [this](const auto & ec, size_t length) { do_send_buffer_handler(ec, length); });
		break;
#endif
	}
}

auto udp2tcp::do_send_buffer_handler(const boost::system::error_code & ec, size_t length) -> void {
	m_tcp_send_in_progress = false;

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "send-buffer [" << to_string() << "]: " << ec.message();
		// Connection failed - close socket so next UDP packet triggers reconnect
		m_app_keep_alive_timer.cancel();
		m_socket_tcp_dest.close();
		// Clear queue since connection is lost - packets would fail anyway
		while (!m_udp_queue.empty()) {
			m_udp_queue.pop();
		}
	} else {
		LOG(trace) << "send-buffer [" << to_string() << "]: sent " << length << " bytes";
		do_app_keep_alive();
		
		// Process queued packets if any
		if (!m_udp_queue.empty()) {
			do_process_queue();
			return;  // do_process_queue will continue the chain
		}
	}

	// Handle next UDP packet (only if no queued packets to process)
	do_send();
}

auto udp2tcp::do_process_queue() -> void {
	if (m_udp_queue.empty()) {
		do_send();
		return;
	}

	if (!m_socket_tcp_dest.is_open()) {
		LOG(debug) << "process-queue: Connection closed, clearing queue (size: " << m_udp_queue.size() << ")";
		while (!m_udp_queue.empty()) {
			m_udp_queue.pop();
		}
		do_send();
		return;
	}

	// Get next packet from queue
	queued_packet pkt = std::move(m_udp_queue.front());
	m_udp_queue.pop();

	LOG(trace) << "process-queue: Processing queued packet (remaining: " << m_udp_queue.size() << ")";

	// CRITICAL: Restore sender endpoint for WireGuard compatibility
	m_ep_udp_sender = pkt.sender;
	
	// Copy data to send buffer
	std::copy(pkt.data.begin(), pkt.data.end(), m_buffer_send.begin());
	m_buffer_send_length = pkt.length;

	// Start async send
	m_tcp_send_in_progress = true;
	do_send_buffer();
}

auto udp2tcp::do_send_handler(const boost::system::error_code & ec, size_t length) -> void {

	if (ec) {
		LOG(error) << "send [" << utils::to_string(m_ep_udp_sender) << "]: " << ec.message();
		// Try to recover from error
		do_send();
		return;
	}

	// Get or create connection for this UDP source (WireGuard peer)
	auto conn = get_or_create_connection(m_ep_udp_sender);
	if (!conn) {
		LOG(warning) << "send: Max connections reached, dropping packet";
		do_send();
		return;
	}

	// Update last activity time
	conn->last_activity = std::chrono::steady_clock::now();

	// If this connection's send is in progress, queue the packet
	if (conn->send_in_progress) {
		// Check queue size limit to prevent unbounded growth
		if (conn->send_queue.size() >= m_max_queue_size) {
			LOG(warning) << "send: Queue full for " << utils::to_string(m_ep_udp_sender) 
			             << ", dropping oldest packet (queue size: " << conn->send_queue.size() << ")";
			conn->send_queue.pop();
		}
		
		// Queue the packet with sender endpoint preserved for WireGuard compatibility
		queued_packet pkt;
		pkt.sender = m_ep_udp_sender;  // CRITICAL: Preserve sender for response routing
		pkt.data.assign(m_buffer_send.begin(), m_buffer_send.begin() + length);
		pkt.length = length;
		conn->send_queue.push(std::move(pkt));
		
		LOG(trace) << "send: Packet queued for " << utils::to_string(m_ep_udp_sender) 
		           << " (queue size: " << conn->send_queue.size() << ")";
		
		// Continue receiving UDP packets while TCP send completes
		do_send();
		return;
	}

	// Copy data to connection's send buffer
	std::copy(m_buffer_send.begin(), m_buffer_send.begin() + length, conn->buffer_send.begin());
	conn->buffer_send_length = length;

	if (!conn->is_connected) {
		do_source_connect(conn);
		// Continue receiving UDP packets while connecting
		do_send();
		return;
	}

	// Start async send
	conn->send_in_progress = true;
	do_source_send_buffer(conn);
	
	// Continue receiving UDP packets (allows concurrent sends to different peers)
	do_send();
}

auto udp2tcp::do_recv_init() -> void {
	switch (m_transport) {
	case utils::transport::raw:
		do_recv(sizeof(utils::ip::udp::header), true);
		break;
#if ENABLE_WEBSOCKET
	case utils::transport::websocket:
		do_ws_recv();
		break;
#endif
	}
}

auto udp2tcp::do_recv(std::size_t rlen, bool ctrl) -> void {
	m_buffer_recv.consume(m_buffer_recv.size()); // Clear any previous data
	asio::async_read(
	    m_socket_tcp_dest, m_buffer_recv, asio::transfer_exactly(rlen),
	    [this, ctrl](const auto & ec, size_t length) { do_recv_handler(ec, length, ctrl); });
}

auto udp2tcp::do_recv_handler(const boost::system::error_code & ec, size_t length, bool ctrl)
    -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "recv: Connection closed: peer="
			           << utils::to_string(m_ep_tcp_dest_cache);
			m_ep_tcp_dest_cache = asio::ip::tcp::endpoint();
			m_app_keep_alive_timer.cancel();
			m_tcp_send_in_progress = false;
			m_socket_tcp_dest.close();
			// Ensure UDP receiver continues - next packet will trigger reconnect
			do_send();
			return;
		}
		LOG(error) << "recv [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_recv_init();
		return;
	}

	LOG(trace) << "recv [" << to_string(true) << "]: len=" << length;

	if (ctrl) {
		auto header =
		    reinterpret_cast<const utils::ip::udp::header *>(m_buffer_recv.data().data());
		if (!header->valid()) {
			LOG(warning) << "recv [" << to_string() << "]: Invalid UDP header";
			// Handle next TCP packet
			do_recv_init();
			return;
		}
		// Check if the packet is a control packet
		if (header->m_length == 0) {
			// Handle next TCP packet
			do_recv_init();
			return;
		}
		// Handle UDP packet payload
		do_recv(header->m_length);
		return;
	}

	if (m_ep_udp_sender.port() != 0) {
		// Copy data to persistent buffer for async send
		auto data = m_buffer_recv.data();
		m_buffer_udp_send_length = asio::buffer_size(data);
		asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
		m_socket_udp_acc.async_send_to(
		    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length), m_ep_udp_sender,
		    [this](const auto & ec, size_t length) { do_udp_send_handler(ec, length); });
		return;
	}

	// Handle next TCP packet
	do_recv_init();
}

auto udp2tcp::do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "udp-send [" << utils::to_string(m_ep_udp_sender) << "]: " << ec.message();
	} else {
		LOG(trace) << "udp-send [" << utils::to_string(m_ep_udp_sender) << "]: len=" << length;
		do_app_keep_alive();
	}

	// Handle next TCP packet
	do_recv_init();
}

#if ENABLE_WEBSOCKET

auto udp2tcp::do_ws_recv() -> void {
	m_ws_buffer_recv.clear();
	m_ws.async_read(m_ws_buffer_recv,
	                [this](const auto & ec, size_t length) { do_ws_recv_handler(ec, length); });
}

auto udp2tcp::do_ws_recv_handler(const boost::system::error_code & ec, size_t length) -> void {

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "recv: Connection closed: peer="
			           << utils::to_string(m_ep_tcp_dest_cache);
			m_ep_tcp_dest_cache = asio::ip::tcp::endpoint();
			m_app_keep_alive_timer.cancel();
			m_tcp_send_in_progress = false;
			m_socket_tcp_dest.close();
			// Ensure UDP receiver continues - next packet will trigger reconnect
			do_send();
			return;
		}
		LOG(error) << "recv [" << to_string() << "]: " << ec.message();
		// Try to recover from error
		do_ws_recv();
		return;
	}

	LOG(trace) << "recv [" << to_string(true) << "]: len=" << length;

	if (m_ep_udp_sender.port() != 0) {
		// Copy data to persistent buffer for async send
		auto data = m_ws_buffer_recv.data();
		m_buffer_udp_send_length = asio::buffer_size(data);
		asio::buffer_copy(asio::buffer(m_buffer_udp_send), data);
		m_socket_udp_acc.async_send_to(
		    asio::buffer(m_buffer_udp_send, m_buffer_udp_send_length), m_ep_udp_sender,
		    [this](const auto & ec, size_t length) { do_ws_udp_send_handler(ec, length); });
		return;
	}

	// Handle next TCP packet
	do_ws_recv();
}

auto udp2tcp::do_ws_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "udp-send [" << utils::to_string(m_ep_udp_sender) << "]: " << ec.message();
	} else {
		LOG(trace) << "udp-send [" << utils::to_string(m_ep_udp_sender) << "]: len=" << length;
	}

	// Handle next TCP packet
	do_ws_recv();
}

#endif

// ============================================================================
// Per-Source Connection Management (for WireGuard peer isolation)
// ============================================================================

auto udp2tcp::get_or_create_connection(const asio::ip::udp::endpoint & source) 
    -> std::shared_ptr<source_connection> {
	std::string key = utils::to_string(source);
	
	auto it = m_source_connections.find(key);
	if (it != m_source_connections.end()) {
		return it->second;
	}
	
	// Check connection limit
	if (m_source_connections.size() >= m_max_connections) {
		LOG(warning) << "get_or_create_connection: Max connections reached (" << m_max_connections << ")";
		return nullptr;
	}
	
	// Create new connection for this source
	auto conn = std::make_shared<source_connection>(m_ioc);
	conn->udp_source = source;
	conn->last_activity = std::chrono::steady_clock::now();
	
	m_source_connections[key] = conn;
	LOG(debug) << "get_or_create_connection: Created new connection for " << key 
	           << " (total: " << m_source_connections.size() << ")";
	
	return conn;
}

auto udp2tcp::do_source_connect(std::shared_ptr<source_connection> conn) -> void {
	try {
		conn->tcp_endpoint = m_ep_tcp_dest_provider.tcp_dest_ep();
		
		// Ensure the socket is in a clean state before connecting
		if (conn->socket.is_open()) {
			conn->socket.close();
		}
		
		// Open the socket with the correct protocol family
		conn->socket.open(conn->tcp_endpoint.protocol());
		
		LOG(debug) << "source-connect: Connecting to " << utils::to_string(conn->tcp_endpoint)
		           << " for " << utils::to_string(conn->udp_source);
		
		conn->socket.async_connect(conn->tcp_endpoint,
		    [this, conn](const auto & ec) { do_source_connect_handler(conn, ec); });
	} catch (const std::exception & e) {
		LOG(error) << "source-connect: Get destination TCP endpoint: " << e.what();
		conn->is_connected = false;
	}
}

auto udp2tcp::do_source_connect_handler(std::shared_ptr<source_connection> conn, 
                                        const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "source-connect [" << utils::to_string(conn->tcp_endpoint)
		           << "]: " << ec.message();
		conn->socket.close();
		conn->is_connected = false;
		return;
	}

	LOG(debug) << "source-connect: Connected to " << utils::to_string(conn->tcp_endpoint)
	           << " for " << utils::to_string(conn->udp_source);

	conn->is_connected = true;

	if (m_tcp_keep_alive_idle_time > 0) {
		LOG(debug) << "tcp-keepalive [" << utils::to_string(conn->socket.remote_endpoint())
		           << "]: idle=" << m_tcp_keep_alive_idle_time;
		utils::socket_set_keep_alive_idle(conn->socket, m_tcp_keep_alive_idle_time);
		conn->socket.set_option(asio::socket_base::keep_alive(true));
		conn->socket.set_option(asio::socket_base::linger(true, 0));
	}

#if ENABLE_WEBSOCKET
	if (m_transport == utils::transport::websocket) {
		// Create WebSocket stream for this connection
		conn->ws_stream = std::make_unique<ws::stream<asio::ip::tcp::socket &>>(conn->socket);
		conn->ws_stream->binary(true);
		
		// Set suggested timeout settings for the websocket client
		conn->ws_stream->set_option(ws::stream_base::timeout::suggested(beast::role_type::client));
		
		// Modify the client handshake request headers
		conn->ws_stream->set_option(ws::stream_base::decorator([this](ws::request_type & req) {
			for (const auto & [key, value] : m_ws_headers)
				req.set(key, value);
		}));
		
		LOG(debug) << "source-connect: WebSocket handshake for " << utils::to_string(conn->udp_source);
		conn->ws_stream->async_handshake("example.com", "/",
		    [this, conn](const auto & ec) { do_source_ws_handshake_handler(conn, ec); });
		return;
	}
#endif

	// Start handling TCP packets for this connection
	do_source_recv_init(conn);

	// Send packet which was waiting for TCP connection
	if (conn->buffer_send_length > 0) {
		conn->send_in_progress = true;
		do_source_send_buffer(conn);
	}
}

#if ENABLE_WEBSOCKET
auto udp2tcp::do_source_ws_handshake_handler(std::shared_ptr<source_connection> conn,
                                              const boost::system::error_code & ec) -> void {
	if (ec) {
		LOG(error) << "source-ws-handshake [" << utils::to_string(conn->tcp_endpoint)
		           << "]: " << ec.message();
		conn->socket.close();
		conn->is_connected = false;
		conn->ws_stream.reset();
		return;
	}

	LOG(debug) << "source-ws-handshake: Completed for " << utils::to_string(conn->udp_source);

	// Start handling TCP packets for this connection
	do_source_recv_init(conn);

	// Send packet which was waiting for TCP connection
	if (conn->buffer_send_length > 0) {
		conn->send_in_progress = true;
		do_source_send_buffer(conn);
	}
}
#endif

auto udp2tcp::do_source_send_buffer(std::shared_ptr<source_connection> conn) -> void {
	LOG(trace) << "source-send [" << utils::to_string(conn->udp_source) << "]: len=" << conn->buffer_send_length;
	
	switch (m_transport) {
	case utils::transport::raw: {
		// Send payload with attached UDP header asynchronously
		conn->tcp_send_header = utils::ip::udp::header(conn->udp_source.port(), m_ep_udp_acc.port(),
		                              static_cast<uint16_t>(conn->buffer_send_length));
		const std::array<asio::const_buffer, 2> iovec{ 
			asio::buffer(&conn->tcp_send_header, sizeof(conn->tcp_send_header)),
			asio::buffer(conn->buffer_send, conn->buffer_send_length) 
		};
		asio::async_write(conn->socket, iovec,
		    [this, conn](const auto & ec, size_t length) { do_source_send_buffer_handler(conn, ec, length); });
	} break;
#if ENABLE_WEBSOCKET
	case utils::transport::websocket:
		if (conn->ws_stream) {
			conn->ws_stream->async_write(asio::buffer(conn->buffer_send, conn->buffer_send_length),
			    [this, conn](const auto & ec, size_t length) { do_source_send_buffer_handler(conn, ec, length); });
		}
		break;
#endif
	}
}

auto udp2tcp::do_source_send_buffer_handler(std::shared_ptr<source_connection> conn,
                                            const boost::system::error_code & ec, size_t length) -> void {
	conn->send_in_progress = false;
	conn->last_activity = std::chrono::steady_clock::now();

	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "source-send-buffer [" << utils::to_string(conn->udp_source) << "]: " << ec.message();
		// Connection failed - mark as disconnected
		conn->socket.close();
		conn->is_connected = false;
#if ENABLE_WEBSOCKET
		conn->ws_stream.reset();
#endif
		// Clear queue since connection is lost
		while (!conn->send_queue.empty()) {
			conn->send_queue.pop();
		}
		return;
	}

	LOG(trace) << "source-send-buffer [" << utils::to_string(conn->udp_source) << "]: sent " << length << " bytes";

	// Process queued packets if any
	if (!conn->send_queue.empty()) {
		do_source_process_queue(conn);
	}
}

auto udp2tcp::do_source_process_queue(std::shared_ptr<source_connection> conn) -> void {
	if (conn->send_queue.empty()) {
		return;
	}

	if (!conn->is_connected || !conn->socket.is_open()) {
		LOG(debug) << "source-process-queue: Connection closed for " << utils::to_string(conn->udp_source)
		           << ", clearing queue (size: " << conn->send_queue.size() << ")";
		while (!conn->send_queue.empty()) {
			conn->send_queue.pop();
		}
		return;
	}

	// Get next packet from queue
	queued_packet pkt = std::move(conn->send_queue.front());
	conn->send_queue.pop();

	LOG(trace) << "source-process-queue: Processing queued packet for " << utils::to_string(conn->udp_source)
	           << " (remaining: " << conn->send_queue.size() << ")";

	// Copy data to send buffer
	std::copy(pkt.data.begin(), pkt.data.end(), conn->buffer_send.begin());
	conn->buffer_send_length = pkt.length;

	// Start async send
	conn->send_in_progress = true;
	do_source_send_buffer(conn);
}

auto udp2tcp::do_source_recv_init(std::shared_ptr<source_connection> conn) -> void {
	switch (m_transport) {
	case utils::transport::raw:
		do_source_recv(conn, sizeof(utils::ip::udp::header), true);
		break;
#if ENABLE_WEBSOCKET
	case utils::transport::websocket:
		do_source_ws_recv(conn);
		break;
#endif
	}
}

auto udp2tcp::do_source_recv(std::shared_ptr<source_connection> conn, std::size_t rlen, bool ctrl) -> void {
	conn->buffer_recv.consume(conn->buffer_recv.size()); // Clear any previous data
	asio::async_read(
	    conn->socket, conn->buffer_recv, asio::transfer_exactly(rlen),
	    [this, conn, ctrl](const auto & ec, size_t length) { do_source_recv_handler(conn, ec, length, ctrl); });
}

auto udp2tcp::do_source_recv_handler(std::shared_ptr<source_connection> conn,
                                     const boost::system::error_code & ec, size_t length, bool ctrl) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "source-recv: Connection closed for " << utils::to_string(conn->udp_source);
			conn->socket.close();
			conn->is_connected = false;
#if ENABLE_WEBSOCKET
			conn->ws_stream.reset();
#endif
			return;
		}
		LOG(error) << "source-recv [" << utils::to_string(conn->udp_source) << "]: " << ec.message();
		// Try to recover from error
		do_source_recv_init(conn);
		return;
	}

	conn->last_activity = std::chrono::steady_clock::now();
	LOG(trace) << "source-recv [" << utils::to_string(conn->udp_source) << "]: len=" << length;

	if (ctrl) {
		auto header = reinterpret_cast<const utils::ip::udp::header *>(conn->buffer_recv.data().data());
		if (!header->valid()) {
			LOG(warning) << "source-recv [" << utils::to_string(conn->udp_source) << "]: Invalid UDP header";
			// Handle next TCP packet
			do_source_recv_init(conn);
			return;
		}
		// Check if the packet is a control packet
		if (header->m_length == 0) {
			// Handle next TCP packet
			do_source_recv_init(conn);
			return;
		}
		// Handle UDP packet payload
		do_source_recv(conn, header->m_length);
		return;
	}

	// CRITICAL: Route response back to correct UDP source for WireGuard compatibility
	if (conn->udp_source.port() != 0) {
		// Copy data to persistent buffer for async send
		auto data = conn->buffer_recv.data();
		conn->buffer_udp_send_length = asio::buffer_size(data);
		asio::buffer_copy(asio::buffer(conn->buffer_udp_send), data);
		m_socket_udp_acc.async_send_to(
		    asio::buffer(conn->buffer_udp_send, conn->buffer_udp_send_length), conn->udp_source,
		    [this, conn](const auto & ec, size_t length) { do_source_udp_send_handler(conn, ec, length); });
		return;
	}

	// Handle next TCP packet
	do_source_recv_init(conn);
}

auto udp2tcp::do_source_udp_send_handler(std::shared_ptr<source_connection> conn,
                                         const boost::system::error_code & ec, size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "source-udp-send [" << utils::to_string(conn->udp_source) << "]: " << ec.message();
	} else {
		LOG(trace) << "source-udp-send [" << utils::to_string(conn->udp_source) << "]: len=" << length;
	}

	// Handle next TCP packet
	do_source_recv_init(conn);
}

#if ENABLE_WEBSOCKET
auto udp2tcp::do_source_ws_recv(std::shared_ptr<source_connection> conn) -> void {
	if (!conn->ws_stream) return;
	
	conn->ws_buffer_recv.clear();
	conn->ws_stream->async_read(conn->ws_buffer_recv,
	    [this, conn](const auto & ec, size_t length) { do_source_ws_recv_handler(conn, ec, length); });
}

auto udp2tcp::do_source_ws_recv_handler(std::shared_ptr<source_connection> conn,
                                        const boost::system::error_code & ec, size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		if (ec == asio::error::eof || ec == asio::error::connection_reset) {
			LOG(debug) << "source-ws-recv: Connection closed for " << utils::to_string(conn->udp_source);
			conn->socket.close();
			conn->is_connected = false;
			conn->ws_stream.reset();
			return;
		}
		LOG(error) << "source-ws-recv [" << utils::to_string(conn->udp_source) << "]: " << ec.message();
		// Try to recover from error
		do_source_ws_recv(conn);
		return;
	}

	conn->last_activity = std::chrono::steady_clock::now();
	LOG(trace) << "source-ws-recv [" << utils::to_string(conn->udp_source) << "]: len=" << length;

	// CRITICAL: Route response back to correct UDP source for WireGuard compatibility
	if (conn->udp_source.port() != 0) {
		// Copy data to persistent buffer for async send
		auto data = conn->ws_buffer_recv.data();
		conn->buffer_udp_send_length = asio::buffer_size(data);
		asio::buffer_copy(asio::buffer(conn->buffer_udp_send), data);
		m_socket_udp_acc.async_send_to(
		    asio::buffer(conn->buffer_udp_send, conn->buffer_udp_send_length), conn->udp_source,
		    [this, conn](const auto & ec, size_t length) { do_source_ws_udp_send_handler(conn, ec, length); });
		return;
	}

	// Handle next TCP packet
	do_source_ws_recv(conn);
}

auto udp2tcp::do_source_ws_udp_send_handler(std::shared_ptr<source_connection> conn,
                                            const boost::system::error_code & ec, size_t length) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "source-ws-udp-send [" << utils::to_string(conn->udp_source) << "]: " << ec.message();
	} else {
		LOG(trace) << "source-ws-udp-send [" << utils::to_string(conn->udp_source) << "]: len=" << length;
	}

	// Handle next TCP packet
	do_source_ws_recv(conn);
}
#endif

auto udp2tcp::do_cleanup_init() -> void {
	// Run cleanup every 30 seconds
	m_cleanup_timer.expires_after(std::chrono::seconds(30));
	m_cleanup_timer.async_wait([this](const auto & ec) { do_cleanup_handler(ec); });
}

auto udp2tcp::do_cleanup_handler(const boost::system::error_code & ec) -> void {
	if (ec) {
		if (ec == asio::error::operation_aborted)
			return;
		LOG(error) << "cleanup: " << ec.message();
		return;
	}

	auto now = std::chrono::steady_clock::now();
	auto timeout = std::chrono::seconds(CONNECTION_IDLE_TIMEOUT);

	std::vector<std::string> to_remove;
	for (auto & [key, conn] : m_source_connections) {
		// Don't remove connections with pending sends
		if (conn->send_in_progress || !conn->send_queue.empty()) {
			continue;
		}
		
		auto idle_time = now - conn->last_activity;
		if (idle_time > timeout) {
			LOG(debug) << "cleanup: Removing idle connection for " << key;
			if (conn->socket.is_open()) {
				conn->socket.close();
			}
#if ENABLE_WEBSOCKET
			conn->ws_stream.reset();
#endif
			to_remove.push_back(key);
		}
	}

	for (const auto & key : to_remove) {
		m_source_connections.erase(key);
	}

	if (!to_remove.empty()) {
		LOG(debug) << "cleanup: Removed " << to_remove.size() << " idle connections (remaining: " 
		           << m_source_connections.size() << ")";
	}

	// Reschedule cleanup
	do_cleanup_init();
}

#if ENABLE_NGROK
auto udp2tcp_dest_provider_ngrok::tcp_dest_ep() -> asio::ip::tcp::endpoint {
	if (!m_endpoint_filter_id.empty()) {
		LOG(debug) << "tcp-provider-ngrok: id=" << m_endpoint_filter_id;
		for (const auto & ep : m_client.endpoints())
			if (ep.id == m_endpoint_filter_id)
				return { ep.address(), ep.port };
		throw std::runtime_error("Endpoint '" + m_endpoint_filter_id + "' not found");
	}
	if (!m_endpoint_filter_uri.empty()) {
		LOG(debug) << "tcp-provider-ngrok: uri=" << m_endpoint_filter_uri;
		auto regex = std::regex(m_endpoint_filter_uri, std::regex::icase);
		for (const auto & ep : m_client.endpoints())
			if (std::regex_match(ep.uri(), regex))
				return { ep.address(), ep.port };
		throw std::runtime_error("Endpoint matching '" + m_endpoint_filter_uri + "' not found");
	}
	throw std::runtime_error("Endpoint filter not set");
}
#endif

}; // namespace wg::tunnel
