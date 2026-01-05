// wg-tcp-tunnel - ngrok.h
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT

#pragma once

#include <cstdint>
#include <ctime>
#include <ostream>
#include <string>
#include <string_view>
#include <vector>

#include <boost/asio.hpp>

namespace wg::ngrok {

namespace asio = boost::asio;

struct endpoint {

	enum class protocol : unsigned char { http, https, tcp, tls };
	static auto protocol_from_string(const std::string_view str) -> protocol;
	static auto protocol_to_string(const protocol proto) -> std::string;

	enum class etype : unsigned char { ephemeral, edge };
	static auto type_from_string(const std::string_view str) -> etype;
	static auto type_to_string(const etype type) -> std::string;

	std::string id;
	std::time_t created_at;
	std::time_t updated_at;
	protocol proto;
	std::string host;
	uint16_t port;
	etype type;

	[[nodiscard]] auto address() const -> asio::ip::address;
	[[nodiscard]] auto uri() const -> std::string;

	friend auto operator<<(std::ostream & os, const endpoint & ep) -> std::ostream & {
		os << ep.id << ": created-at=" << ep.created_at << " updated-at=" << ep.updated_at
		   << " type=" << type_to_string(ep.type) << " uri=" << ep.uri();
		return os;
	}
};

class client {
public:
	explicit client(const std::string_view key) : m_key(key) {}
	~client() = default;

	auto endpoints() -> std::vector<endpoint>;

private:
	std::string m_key;
};

} // namespace wg::ngrok
