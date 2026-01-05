// wg-tcp-tunnel - utils.hpp
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <boost/asio.hpp>
#include <boost/crc.hpp>

namespace wg::utils {

namespace asio = boost::asio;

enum class transport {
	raw,
#if ENABLE_TLS
	tls,
#endif
#if ENABLE_WEBSOCKET
	websocket,
#if ENABLE_TLS
	wss, // TLS + WebSocket
#endif
#endif
};

#if ENABLE_TLS
// TLS configuration structure
struct tls_config {
	std::string cert_path;      // Server certificate file path
	std::string key_path;       // Server private key file path
	std::string ca_path;        // CA certificate file path (for verification)
	bool verify = true;         // Enable certificate verification
	bool allow_self_signed = false; // Allow self-signed certificates
	bool skip_verification = false; // Skip all verification (insecure)
};
#endif

namespace ip {
namespace udp {

struct header {

	header(uint16_t src_port, uint16_t dst_port, uint16_t length)
	    : m_src_port(src_port), m_dst_port(dst_port), m_length(length) {
		boost::crc_16_type crc16;
		crc16.process_bytes(this, sizeof(*this) - sizeof(m_crc16));
		m_crc16 = crc16.checksum();
	}

	[[nodiscard]] auto valid() const -> bool {
		boost::crc_16_type crc16;
		crc16.process_bytes(this, sizeof(*this) - sizeof(m_crc16));
		return crc16.checksum() == m_crc16;
	}

	uint16_t m_src_port;
	uint16_t m_dst_port;
	uint16_t m_length;
	uint16_t m_crc16;
};

// Make sure the header structure is not padded
static_assert(sizeof(header) == 8, "Invalid UDP header size");

}; // namespace udp
}; // namespace ip

namespace http {

using header = std::pair<std::string, std::string>;
using headers = std::vector<header>;

static inline auto split_header(const std::string_view str) -> header {
	auto pos = str.find_first_of(':');
	if (pos == std::string::npos)
		throw std::runtime_error("Unable to split HTTP header");
	// Trim any leading spaces from the value
	auto pos2 = str.substr(pos + 1).find_first_not_of(' ');
	return { std::string(str.substr(0, pos)), std::string(str.substr(pos + 1 + pos2)) };
}

}; // namespace http

static inline auto split_host_port(const std::string_view str)
    -> std::pair<std::string, uint16_t> {
	auto pos = str.find_last_of(':');
	if (pos == std::string::npos)
		throw std::runtime_error("Unable to split host and port");
	return { std::string(str.substr(0, pos)), std::stoi(std::string(str.substr(pos + 1))) };
}

static inline auto to_string(const asio::ip::tcp::endpoint & ep) -> std::string {
	return "tcp:" + ep.address().to_string() + ":" + std::to_string(ep.port());
}

static inline auto to_string(const asio::ip::udp::endpoint & ep) -> std::string {
	return "udp:" + ep.address().to_string() + ":" + std::to_string(ep.port());
}

static inline auto socket_set_keep_alive_idle(asio::ip::tcp::socket & socket, int time) -> int {
	boost::system::error_code ec;
	socket.set_option(asio::detail::socket_option::integer<IPPROTO_TCP, TCP_KEEPIDLE>(time), ec);
	return ec.value();
}

} // namespace wg::utils
