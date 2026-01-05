// wg-tcp-tunnel - udp2tcp.h
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#pragma once

#include <array>
#include <chrono>
#include <cstddef>
#include <memory>
#include <queue>
#include <string>
#include <unordered_map>
#include <vector>

#include <boost/asio.hpp>
#if ENABLE_TLS
#	include <boost/asio/ssl.hpp>
#endif
#if ENABLE_WEBSOCKET
#	include <boost/beast/websocket.hpp>
#endif
#if ENABLE_TLS && ENABLE_WEBSOCKET
#	include <boost/beast/ssl.hpp>
#endif

#include "ngrok.h"
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
using std::size_t;

class udp2tcp_dest_provider {
public:
	virtual auto tcp_dest_ep() -> asio::ip::tcp::endpoint = 0;
};

class udp2tcp {
public:
	udp2tcp(asio::io_context & ioc, asio::ip::udp::endpoint ep_udp_acc,
	        udp2tcp_dest_provider & ep_tcp_dest_provider)
	    : m_ioc(ioc), m_ep_udp_acc(std::move(ep_udp_acc)), m_socket_udp_acc(ioc, m_ep_udp_acc),
	      m_socket_tcp_dest(ioc), m_ep_tcp_dest_provider(ep_tcp_dest_provider),
	      m_app_keep_alive_timer(ioc), m_cleanup_timer(ioc) {}
	~udp2tcp() = default;

	auto run(utils::transport transport) -> void;

	auto keep_alive_app(int idle_time) -> void { m_app_keep_alive_idle_time = idle_time; }
	auto keep_alive_tcp(int idle_time) -> void { m_tcp_keep_alive_idle_time = idle_time; }
	auto max_connections(size_t max) -> void { m_max_connections = max; }
	auto max_queue_size(size_t max) -> void { m_max_queue_size = max; }
#if ENABLE_TLS
	auto tls_config(utils::tls_config config) -> void { m_tls_config = std::move(config); }
#endif
#if ENABLE_WEBSOCKET
	auto ws_headers(utils::http::headers headers) { m_ws_headers = std::move(headers); }
#endif

private:
	auto to_string(bool verbose = false) -> std::string;

	auto do_connect() -> void;
	auto do_connect_handler(const boost::system::error_code & ec) -> void;
#if ENABLE_TLS
	auto do_tls_handshake_handler(const boost::system::error_code & ec) -> void;
#endif
#if ENABLE_WEBSOCKET
	auto do_ws_handshake_handler(const boost::system::error_code & ec) -> void;
#endif

	auto do_app_keep_alive_init() -> void;
	auto do_app_keep_alive(bool init = false) -> void;
	auto do_app_keep_alive_handler(const boost::system::error_code & ec) -> void;

	auto do_send() -> void;
	auto do_send_buffer() -> void;
	auto do_send_buffer_handler(const boost::system::error_code & ec, size_t length) -> void;
	auto do_send_handler(const boost::system::error_code & ec, size_t length) -> void;
	auto do_keepalive_send_handler(const boost::system::error_code & ec, size_t length) -> void;

	auto do_recv_init() -> void;
	auto do_recv(size_t rlen, bool ctrl = false) -> void;
	auto do_recv_handler(const boost::system::error_code & ec, size_t length, bool ctrl) -> void;
	auto do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

#if ENABLE_WEBSOCKET
	auto do_ws_recv() -> void;
	auto do_ws_recv_handler(const boost::system::error_code & ec, size_t length) -> void;
	auto do_ws_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;
#endif

	// Structure for queued UDP packets (preserves sender endpoint for WireGuard compatibility)
	struct queued_packet {
		asio::ip::udp::endpoint sender;  // CRITICAL: Preserve for WireGuard routing
		std::vector<char> data;
		size_t length;
	};

	// Per-source TCP connection structure for WireGuard peer isolation
	struct source_connection {
		asio::ip::tcp::socket socket;
		asio::ip::udp::endpoint udp_source;  // CRITICAL: Preserve for response routing
		asio::ip::tcp::endpoint tcp_endpoint;
		bool is_connected = false;
		bool send_in_progress = false;
		std::chrono::steady_clock::time_point last_activity;
		std::queue<queued_packet> send_queue;
		std::array<char, 65536> buffer_send;
		size_t buffer_send_length = 0;
		asio::streambuf buffer_recv;
		std::array<char, 65536> buffer_udp_send;
		size_t buffer_udp_send_length = 0;
		utils::ip::udp::header tcp_send_header{ 0, 0, 0 };
#if ENABLE_TLS
		std::unique_ptr<ssl::stream<asio::ip::tcp::socket &>> ssl_stream;
#endif
#if ENABLE_WEBSOCKET
		std::unique_ptr<ws::stream<asio::ip::tcp::socket &>> ws_stream;
#if ENABLE_TLS
		std::unique_ptr<ws::stream<ssl::stream<asio::ip::tcp::socket &> &>> wss_stream;
#endif
		beast::flat_buffer ws_buffer_recv;
#endif

		source_connection(asio::io_context & ioc) : socket(ioc) {}
	};

	// Get or create connection for a UDP source
	auto get_or_create_connection(const asio::ip::udp::endpoint & source) -> std::shared_ptr<source_connection>;
	
	// Per-source connection methods
	auto do_source_connect(std::shared_ptr<source_connection> conn) -> void;
	auto do_source_connect_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec) -> void;
	auto do_source_send_buffer(std::shared_ptr<source_connection> conn) -> void;
	auto do_source_send_buffer_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec, size_t length) -> void;
	auto do_source_process_queue(std::shared_ptr<source_connection> conn) -> void;
	auto do_source_recv_init(std::shared_ptr<source_connection> conn) -> void;
	auto do_source_recv(std::shared_ptr<source_connection> conn, size_t rlen, bool ctrl = false) -> void;
	auto do_source_recv_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec, size_t length, bool ctrl) -> void;
	auto do_source_udp_send_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec, size_t length) -> void;
#if ENABLE_TLS
	auto do_source_tls_handshake_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec) -> void;
#endif
#if ENABLE_WEBSOCKET
	auto do_source_ws_handshake_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec) -> void;
	auto do_source_ws_recv(std::shared_ptr<source_connection> conn) -> void;
	auto do_source_ws_recv_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec, size_t length) -> void;
	auto do_source_ws_udp_send_handler(std::shared_ptr<source_connection> conn, const boost::system::error_code & ec, size_t length) -> void;
#endif

	// Connection cleanup
	auto do_cleanup_init() -> void;
	auto do_cleanup_handler(const boost::system::error_code & ec) -> void;

	// Process next packet from queue (legacy single-connection)
	auto do_process_queue() -> void;

	// Reference to io_context for creating new connections
	asio::io_context & m_ioc;
	
	asio::ip::udp::endpoint m_ep_udp_acc;
	asio::ip::udp::endpoint m_ep_udp_sender;
	asio::ip::udp::socket m_socket_udp_acc;
	asio::ip::tcp::socket m_socket_tcp_dest;  // Legacy single connection (for compatibility)
	
	// Per-source connection map for WireGuard peer isolation
	std::unordered_map<std::string, std::shared_ptr<source_connection>> m_source_connections;
	size_t m_max_connections = 100;  // Max concurrent connections (configurable)
	static constexpr int CONNECTION_IDLE_TIMEOUT = 120;  // Seconds before cleanup
	asio::system_timer m_cleanup_timer;
	
	// UDP packet queue to buffer packets when TCP send is busy (legacy)
	std::queue<queued_packet> m_udp_queue;
	size_t m_max_queue_size = 1000; // Prevent unbounded growth (configurable via MAX_QUEUE_SIZE env var)
	// Provider for obtaining TCP destination endpoint
	udp2tcp_dest_provider & m_ep_tcp_dest_provider;
	asio::ip::tcp::endpoint m_ep_tcp_dest_cache;
	// Transport protocol used for the TCP connection
	utils::transport m_transport = utils::transport::raw;
	// Application keep-alive idle time in seconds, 0 to disable
	int m_app_keep_alive_idle_time = 0;
	asio::system_timer m_app_keep_alive_timer;
	// TCP keep-alive idle time in seconds, 0 to disable
	int m_tcp_keep_alive_idle_time = 0;
	// Buffers for sending and receiving data
	// Increased from 4096 to 65536 (64KB) to handle more packets before dropping
	std::array<char, 65536> m_buffer_send;
	size_t m_buffer_send_length;
	asio::streambuf m_buffer_recv;
	// Buffer for async UDP response send (must persist during async op)
	// Increased from 4096 to 65536 (64KB) to match send buffer
	std::array<char, 65536> m_buffer_udp_send;
	size_t m_buffer_udp_send_length = 0;
	// Header buffer for async TCP send operations (must persist during async op)
	utils::ip::udp::header m_tcp_send_header{ 0, 0, 0 };
	// Flag to indicate if a TCP send is in progress (prevent overlapping sends)
	bool m_tcp_send_in_progress = false;
#if ENABLE_TLS
	// TLS configuration
	utils::tls_config m_tls_config;
	// SSL context for TLS connections
	std::unique_ptr<ssl::context> m_ssl_ctx;
	// SSL stream for legacy single connection
	std::unique_ptr<ssl::stream<asio::ip::tcp::socket &>> m_ssl_stream;
	// Initialize SSL context
	auto init_ssl_context() -> bool;
#endif
#if ENABLE_WEBSOCKET
	ws::stream<asio::ip::tcp::socket &> m_ws{ m_socket_tcp_dest };
#if ENABLE_TLS
	std::unique_ptr<ws::stream<ssl::stream<asio::ip::tcp::socket &> &>> m_wss;
#endif
	beast::flat_buffer m_ws_buffer_recv;
	// List of WebSocket custom headers used during the handshake
	utils::http::headers m_ws_headers;
#endif
};

class udp2tcp_dest_provider_simple : virtual public udp2tcp_dest_provider {
public:
	udp2tcp_dest_provider_simple(asio::ip::tcp::endpoint ep) : m_ep(std::move(ep)) {}
	auto tcp_dest_ep() -> asio::ip::tcp::endpoint override { return m_ep; }

private:
	asio::ip::tcp::endpoint m_ep;
};

#if ENABLE_NGROK
class udp2tcp_dest_provider_ngrok : virtual public udp2tcp_dest_provider {
public:
	udp2tcp_dest_provider_ngrok(wg::ngrok::client & client) : m_client(client) {}
	auto tcp_dest_ep() -> asio::ip::tcp::endpoint override;

	auto filter_id(const std::string_view id) -> void { m_endpoint_filter_id = id; }
	auto filter_uri(const std::string_view uri) -> void { m_endpoint_filter_uri = uri; }

private:
	wg::ngrok::client & m_client;
	std::string m_endpoint_filter_id;
	std::string m_endpoint_filter_uri;
};
#endif

}; // namespace wg::tunnel
