// wg-tcp-tunnel - tcp2udp.h
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#pragma once

#include <array>
#include <cstddef>
#include <memory>
#include <string>
#include <utility>

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

class tcp2udp {
public:
	tcp2udp(asio::io_context & ioc, asio::ip::tcp::endpoint ep_tcp_acc,
	        asio::ip::udp::endpoint ep_udp_dest)
	    : m_io_context(ioc), m_ep_tcp_acc(std::move(ep_tcp_acc)),
	      m_ep_udp_dest(std::move(ep_udp_dest)), m_tcp_acceptor(ioc, m_ep_tcp_acc) {}
	~tcp2udp() = default;

	auto run(utils::transport transport) -> void;

	auto keep_alive_app(int idle_time) -> void { m_app_keep_alive_idle_time = idle_time; }
	auto keep_alive_tcp(int idle_time) -> void { m_tcp_keep_alive_idle_time = idle_time; }
#if ENABLE_TLS
	auto tls_config(utils::tls_config config) -> void { m_tls_config = std::move(config); }
#endif
#if ENABLE_WEBSOCKET
	auto ws_headers(utils::http::headers headers) { m_ws_headers = std::move(headers); }
#endif

private:
	union tcp {
		class session {
		public:
			session(tcp2udp & tcp2udp, asio::ip::tcp::socket socket)
			    : m_socket(std::move(socket)), m_socket_udp_dest(tcp2udp.m_io_context),
			      m_socket_ep_remote(m_socket.remote_endpoint()) {
				m_socket_udp_dest.connect(tcp2udp.m_ep_udp_dest);
			}

		protected:
			auto to_string(bool verbose = false) -> std::string;

			asio::ip::tcp::socket m_socket;
			asio::ip::udp::socket m_socket_udp_dest;
			// Saved remote endpoint of the TCP socket, so we can get
			// the address after the socket is disconnected
			asio::ip::tcp::endpoint m_socket_ep_remote;
		};

		class session_raw : public session, public std::enable_shared_from_this<session_raw> {
		public:
			session_raw(tcp2udp & tcp2udp, asio::ip::tcp::socket socket)
			    : session(tcp2udp, std::move(socket)) {}

			auto run() -> void;

		private:
			auto do_send_init() -> void;
			auto do_send(size_t rlen, bool ctrl = false) -> void;
			auto do_send_handler(const boost::system::error_code & ec, size_t length, bool ctrl)
			    -> void;
			auto do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			auto do_recv() -> void;
			auto do_recv_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_tcp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			asio::streambuf m_buffer_send;
			std::array<char, 4096> m_buffer_recv;
			// Buffer for async UDP send (must persist during async op)
			std::array<char, 4096> m_buffer_udp_send;
			size_t m_buffer_udp_send_length = 0;
			// Header buffer for async TCP send (must persist during async op)
			utils::ip::udp::header m_tcp_send_header{ 0, 0, 0 };
			size_t m_tcp_recv_length = 0;
			bool m_initialized = false;
		};

#if ENABLE_WEBSOCKET
		class session_ws : public session, public std::enable_shared_from_this<session_ws> {
		public:
			session_ws(tcp2udp & tcp2udp, asio::ip::tcp::socket socket)
			    : session(tcp2udp, std::move(socket)), m_ws(m_socket),
			      m_ws_headers(tcp2udp.m_ws_headers) {}

			auto run() -> void;

		private:
			auto do_accept() -> void;
			auto do_accept_handler(const boost::system::error_code & ec) -> void;

			auto do_send() -> void;
			auto do_send_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			auto do_recv() -> void;
			auto do_recv_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_ws_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			ws::stream<asio::ip::tcp::socket &> m_ws;
			utils::http::headers & m_ws_headers;
			beast::flat_buffer m_buffer_send;
			std::array<char, 4096> m_buffer_recv;
			// Buffer for async UDP send (must persist during async op)
			std::array<char, 4096> m_buffer_udp_send;
			size_t m_buffer_udp_send_length = 0;
			size_t m_ws_recv_length = 0;
		};
#endif

#if ENABLE_TLS
		// TLS session - uses SSL stream over TCP socket
		class session_tls : public std::enable_shared_from_this<session_tls> {
		public:
			session_tls(tcp2udp & tcp2udp, asio::ip::tcp::socket socket, ssl::context & ssl_ctx)
			    : m_ssl_stream(std::move(socket), ssl_ctx),
			      m_socket_udp_dest(tcp2udp.m_io_context),
			      m_socket_ep_remote(m_ssl_stream.lowest_layer().remote_endpoint()) {
				m_socket_udp_dest.connect(tcp2udp.m_ep_udp_dest);
			}

			auto run() -> void;

		private:
			auto to_string(bool verbose = false) -> std::string;
			auto do_handshake() -> void;
			auto do_handshake_handler(const boost::system::error_code & ec) -> void;

			auto do_send_init() -> void;
			auto do_send(size_t rlen, bool ctrl = false) -> void;
			auto do_send_handler(const boost::system::error_code & ec, size_t length, bool ctrl)
			    -> void;
			auto do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			auto do_recv() -> void;
			auto do_recv_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_tls_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			ssl::stream<asio::ip::tcp::socket> m_ssl_stream;
			asio::ip::udp::socket m_socket_udp_dest;
			asio::ip::tcp::endpoint m_socket_ep_remote;
			asio::streambuf m_buffer_send;
			std::array<char, 4096> m_buffer_recv;
			std::array<char, 4096> m_buffer_udp_send;
			size_t m_buffer_udp_send_length = 0;
			utils::ip::udp::header m_tcp_send_header{ 0, 0, 0 };
			size_t m_tcp_recv_length = 0;
			bool m_initialized = false;
		};

#if ENABLE_WEBSOCKET
		// WSS session - WebSocket over TLS
		class session_wss : public std::enable_shared_from_this<session_wss> {
		public:
			session_wss(tcp2udp & tcp2udp, asio::ip::tcp::socket socket, ssl::context & ssl_ctx)
			    : m_ssl_stream(std::move(socket), ssl_ctx),
			      m_ws(m_ssl_stream),
			      m_socket_udp_dest(tcp2udp.m_io_context),
			      m_socket_ep_remote(m_ssl_stream.lowest_layer().remote_endpoint()),
			      m_ws_headers(tcp2udp.m_ws_headers) {
				m_socket_udp_dest.connect(tcp2udp.m_ep_udp_dest);
			}

			auto run() -> void;

		private:
			auto to_string(bool verbose = false) -> std::string;
			auto do_tls_handshake() -> void;
			auto do_tls_handshake_handler(const boost::system::error_code & ec) -> void;

			auto do_accept() -> void;
			auto do_accept_handler(const boost::system::error_code & ec) -> void;

			auto do_send() -> void;
			auto do_send_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_udp_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			auto do_recv() -> void;
			auto do_recv_handler(const boost::system::error_code & ec, size_t length) -> void;
			auto do_ws_send_handler(const boost::system::error_code & ec, size_t length) -> void;

			ssl::stream<asio::ip::tcp::socket> m_ssl_stream;
			ws::stream<ssl::stream<asio::ip::tcp::socket> &> m_ws;
			asio::ip::udp::socket m_socket_udp_dest;
			asio::ip::tcp::endpoint m_socket_ep_remote;
			utils::http::headers & m_ws_headers;
			beast::flat_buffer m_buffer_send;
			std::array<char, 4096> m_buffer_recv;
			std::array<char, 4096> m_buffer_udp_send;
			size_t m_buffer_udp_send_length = 0;
			size_t m_ws_recv_length = 0;
		};
#endif // ENABLE_WEBSOCKET
#endif // ENABLE_TLS
	};

	auto do_accept() -> void;
	auto do_accept_handler(const boost::system::error_code & ec, asio::ip::tcp::socket peer)
	    -> void;

	asio::io_context & m_io_context;
	asio::ip::tcp::endpoint m_ep_tcp_acc;
	asio::ip::udp::endpoint m_ep_udp_dest;
	asio::ip::tcp::acceptor m_tcp_acceptor;
	// Transport protocol used for the TCP connection
	utils::transport m_transport = utils::transport::raw;
	// Application keep-alive idle time in seconds, 0 to disable
	int m_app_keep_alive_idle_time = 0;
	// TCP keep-alive idle time in seconds, 0 to disable
	int m_tcp_keep_alive_idle_time = 0;
#if ENABLE_TLS
	// TLS configuration
	utils::tls_config m_tls_config;
	// SSL context for TLS sessions
	std::unique_ptr<ssl::context> m_ssl_ctx;
	// Initialize SSL context
	auto init_ssl_context() -> bool;
#endif
#if ENABLE_WEBSOCKET
	// List of WebSocket custom headers used during the handshake
	utils::http::headers m_ws_headers;
#endif
};

}; // namespace wg::tunnel
