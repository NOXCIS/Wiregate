// wg-tcp-tunnel - main.cpp
// SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
// SPDX-License-Identifier: MIT
// Build: TLS+WebSocket enabled

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include <boost/asio.hpp>
#include <boost/log/core.hpp>
#include <boost/log/expressions.hpp>
#include <boost/log/trivial.hpp>
#include <boost/log/utility/setup/console.hpp>
#include <boost/program_options.hpp>

#include "ngrok.h"
#include "tcp2udp.h"
#include "udp2tcp.h"
#include "utils.hpp"
#include "version.h"

namespace asio = boost::asio;
namespace logging = boost::log;
namespace po = boost::program_options;
using std::size_t;

namespace boost {

namespace asio::ip {

template <typename T>
auto validate(boost::any & v, const std::vector<std::string> & values, T *, int) -> void {
	po::validators::check_first_occurrence(v);
	const std::string & s = po::validators::get_single_string(values);
	auto pos = s.find_last_of(':');
	if (pos == std::string::npos)
		throw po::error_with_option_name(
		    "unable to split IP address and port in option '%canonical_option%'");
	try {
		auto addr = asio::ip::make_address(s.substr(0, pos));
		auto port = std::stoi(s.substr(pos + 1));
		if (port < 0 || port > 65535)
			throw po::error_with_option_name(
			    "the port number in option '%canonical_option%' is invalid");
		v = boost::any(T(addr, static_cast<unsigned short>(port)));
	} catch (const boost::system::system_error &) {
		throw po::error_with_option_name(
		    "the IP address in option '%canonical_option%' is invalid");
	} catch (const std::exception &) {
		throw po::error_with_option_name(
		    "the port number in option '%canonical_option%' is invalid");
	}
}

}; // namespace asio::ip

namespace program_options {

class counter : public typed_value<size_t> {
public:
	counter(size_t * store = nullptr) : typed_value<size_t>(store) {
		// Make counter a non-value option
		default_value(0);
		zero_tokens();
	}
	~counter() override = default;
	auto xparse(boost::any & store, const std::vector<std::string> &) const -> void override {
		// Increment counter on each option occurrence
		store = boost::any(++m_count);
	}

private:
	mutable size_t m_count{ 0 };
};

}; // namespace program_options

auto validate(boost::any & v, const std::vector<std::string> & values, wg::utils::http::headers *,
              int) -> void {
	const std::string & s = po::validators::get_single_string(values);
	if (v.empty())
		v = boost::any(wg::utils::http::headers());
	try {
		auto & headers = boost::any_cast<wg::utils::http::headers &>(v);
		headers.push_back(wg::utils::http::split_header(s));
	} catch (const std::exception &) {
		throw po::error_with_option_name(
		    "the HTTP header in option '%canonical_option%' is invalid");
	}
}

}; // namespace boost

auto main(int argc, char * argv[]) -> int {

	auto transport = wg::utils::transport::raw;
	asio::ip::tcp::endpoint ep_src_tcp;
	asio::ip::udp::endpoint ep_dst_udp;
	asio::ip::udp::endpoint ep_src_udp;
	asio::ip::tcp::endpoint ep_dst_tcp;
	int tcp_keep_alive = 0;
	size_t count_verbose;
	size_t count_quiet;
	size_t max_connections = 100;

	po::options_description options("Options");
	auto o_builder = options.add_options();
	o_builder("help,h", "print this help message and exit");
	o_builder("version,V", "print version and exit");
	o_builder("verbose,v", new po::counter(&count_verbose), "increase verbosity level");
	o_builder("quiet,q", new po::counter(&count_quiet), "decrease verbosity level");
	o_builder("src-tcp,T", po::value(&ep_src_tcp), "source TCP address and port");
	auto dst_udp_default = asio::ip::udp::endpoint(asio::ip::make_address("127.0.0.1"), 51820);
	o_builder("dst-udp,u", po::value(&ep_dst_udp)->default_value(dst_udp_default),
	          "destination UDP address and port");
	o_builder("src-udp,U", po::value(&ep_src_udp), "source UDP address and port");
	o_builder("dst-tcp,t", po::value(&ep_dst_tcp), "destination TCP address and port");
	o_builder("tcp-keep-alive", po::value(&tcp_keep_alive)->implicit_value(120),
	          "enable TCP keep-alive on TCP socket(s) optionally specifying the keep-alive "
	          "idle time in seconds");
	o_builder("max-connections", po::value(&max_connections)->default_value(100),
	          "maximum number of concurrent TCP connections per UDP source (default: 100)");

#if ENABLE_TLS
	bool tls = false;
	std::string tls_cert;
	std::string tls_key;
	std::string tls_ca;
	bool tls_verify = true;
	bool tls_allow_self_signed = false;
	bool tls_skip_verification = false;
	o_builder("tls,S", po::bool_switch(&tls), "enable TLS/SSL encryption");
	o_builder("tls-cert", po::value(&tls_cert), "server certificate file path (PEM format)");
	o_builder("tls-key", po::value(&tls_key), "server private key file path (PEM format)");
	o_builder("tls-ca", po::value(&tls_ca), "CA certificate file path for verification (PEM format)");
	o_builder("tls-no-verify", po::bool_switch()->notifier([&tls_verify](bool v) { if (v) tls_verify = false; }),
	          "disable certificate verification");
	o_builder("tls-allow-self-signed", po::bool_switch(&tls_allow_self_signed),
	          "allow self-signed certificates");
	o_builder("tls-skip-verification", po::bool_switch(&tls_skip_verification),
	          "skip all certificate verification (insecure, testing only)");
#endif

#if ENABLE_WEBSOCKET
	bool websocket = false;
	wg::utils::http::headers websocket_headers;
	o_builder("web-socket,W", po::bool_switch(&websocket), "enable WebSocket transport mode");
	o_builder("web-socket-header,H", po::value(&websocket_headers)->composing(),
	          "add WebSocket header; may be specified multiple times");
#endif

#if ENABLE_NGROK
	std::string ngrok_api_key;
	std::string ngrok_dst_tcp_endpoint;
	int ngrok_keep_alive = 0;
	o_builder("ngrok-api-key", po::value(&ngrok_api_key)->default_value("ENV:NGROK_API_KEY"),
	          "NGROK API key or 'ENV:VARIABLE' to read the key from the environment variable");
	o_builder("ngrok-dst-tcp-endpoint", po::value(&ngrok_dst_tcp_endpoint),
	          "NGROK endpoint used to forward TCP traffic; the endpoint can be specified as "
	          "'id=ID' or 'uri=REGEX', where ID is the endpoint identifier and REGEX is a "
	          "regular expression matching the endpoint URI; the special value 'list' can be "
	          "used to list all available endpoints");
	o_builder("ngrok-keep-alive", po::value(&ngrok_keep_alive)->implicit_value(270),
	          "enable keep-alive for NGROK connection");
#endif

	po::variables_map args;
	try {
		po::store(po::parse_command_line(argc, argv, options), args);
		po::notify(args);
	} catch (const std::exception & e) {
		std::cerr << PROJECT_NAME << ": " << e.what() << "\n";
		return EXIT_FAILURE;
	}

	if (args.count("help")) {
		std::cout << "Usage:" << "\n"
		          << "  " << PROJECT_NAME << " [OPTION]..." << "\n"
		          << "\n"
		          << options << "\n"
		          << "Examples:" << "\n"
		          << "  " << PROJECT_NAME << " --src-tcp=127.0.0.1:12345 --dst-udp=127.0.0.1:51820"
		          << "\n"
		          << "  " << PROJECT_NAME << " --src-udp=127.0.0.1:51821 --dst-tcp=127.0.0.1:12345"
		          << "\n";
		return EXIT_SUCCESS;
	}
	if (args.count("version")) {
		std::cout << PROJECT_NAME << " " << PROJECT_VERSION << "\n";
		return EXIT_SUCCESS;
	}

#if ENABLE_SYSTEMD
	if (std::getenv("INVOCATION_ID") != nullptr)
		// If launched by systemd we do not need timestamp in our log message
		logging::add_console_log(std::clog, logging::keywords::format = "[%Severity%] %Message%");
#endif

	const int verbose = count_verbose - count_quiet;
	if (verbose < 0) {
		logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::error);
	} else if (verbose == 0) {
		logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::warning);
	} else if (verbose == 1) {
		logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::info);
	} else if (verbose == 2) {
		logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::debug);
	} else {
		logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::trace);
	}

	wg::tunnel::udp2tcp_dest_provider_simple udp2tcp_dest_provider_simple(ep_dst_tcp);
	wg::tunnel::udp2tcp_dest_provider * udp2tcp_dest_provider = &udp2tcp_dest_provider_simple;
	bool dynamic_dst_tcp = false;

#if ENABLE_NGROK

	if (ngrok_api_key.substr(0, 4) == "ENV:") {
		// Read NGROK API key from the environment variable
		const auto key = std::getenv(ngrok_api_key.substr(4).c_str());
		ngrok_api_key = key != nullptr ? key : "";
	}

	wg::ngrok::client ngrok(ngrok_api_key);
	wg::tunnel::udp2tcp_dest_provider_ngrok udp2tcp_dest_provider_ngrok(ngrok);

	if (!ngrok_dst_tcp_endpoint.empty()) {
		try {
			if (ngrok_dst_tcp_endpoint == "list") {
				for (const auto & ep : ngrok.endpoints())
					std::cout << ep << "\n";
				return EXIT_SUCCESS;
			} else if (ngrok_dst_tcp_endpoint.substr(0, 3) == "id=") {
				udp2tcp_dest_provider_ngrok.filter_id(ngrok_dst_tcp_endpoint.substr(3));
				udp2tcp_dest_provider = &udp2tcp_dest_provider_ngrok;
				dynamic_dst_tcp = true;
			} else if (ngrok_dst_tcp_endpoint.substr(0, 4) == "uri=") {
				udp2tcp_dest_provider_ngrok.filter_uri(ngrok_dst_tcp_endpoint.substr(4));
				udp2tcp_dest_provider = &udp2tcp_dest_provider_ngrok;
				dynamic_dst_tcp = true;
			} else {
				throw std::runtime_error("Invalid NGROK endpoint specification");
			}
		} catch (const std::exception & e) {
			std::cerr << PROJECT_NAME << ": " << e.what() << "\n";
			return EXIT_FAILURE;
		}
	}

#endif

	const bool is_server = ep_src_tcp.port() != 0 && ep_dst_udp.port() != 0;
	const bool is_client = ep_src_udp.port() != 0 && (ep_dst_tcp.port() != 0 || dynamic_dst_tcp);
	if (!is_server && !is_client) {
		std::cerr << PROJECT_NAME << ": one of "
		          << "'--src-tcp' && '--dst-udp'"
		          << " or "
		          << "'--src-udp' && '--dst-tcp'"
		          << " must be given" << "\n";
		return EXIT_FAILURE;
	}

#if ENABLE_TLS
	// Validate TLS options
	if (tls) {
		// Server mode requires cert and key
		if (is_server && (tls_cert.empty() || tls_key.empty())) {
			std::cerr << PROJECT_NAME << ": TLS server mode requires '--tls-cert' and '--tls-key'" << "\n";
			return EXIT_FAILURE;
		}
		if (tls_skip_verification) {
			std::cerr << PROJECT_NAME << ": WARNING: TLS verification is disabled. "
			          << "This is insecure and should only be used for testing." << "\n";
		}
	}
	if (!tls && (!tls_cert.empty() || !tls_key.empty() || !tls_ca.empty())) {
		std::cerr << PROJECT_NAME << ": TLS certificate options require '--tls' to be enabled" << "\n";
		return EXIT_FAILURE;
	}
#endif

#if ENABLE_WEBSOCKET
	if (websocket_headers.size() > 0 && !websocket) {
		std::cerr << PROJECT_NAME << ": '--web-socket-header' can be used only with "
		          << "the WebSocket transport mode enabled" << "\n";
		return EXIT_FAILURE;
	}
#endif

	// Check for MAX_CONNECTIONS environment variable (overrides command-line default)
	const char * env_max_connections = std::getenv("MAX_CONNECTIONS");
	if (env_max_connections != nullptr) {
		try {
			max_connections = std::stoul(env_max_connections);
			if (max_connections == 0) {
				std::cerr << PROJECT_NAME << ": MAX_CONNECTIONS must be greater than 0" << "\n";
				return EXIT_FAILURE;
			}
		} catch (const std::exception &) {
			std::cerr << PROJECT_NAME << ": Invalid MAX_CONNECTIONS environment variable value" << "\n";
			return EXIT_FAILURE;
		}
	}

	asio::io_context ioc;
	wg::tunnel::tcp2udp tcp2udp(ioc, ep_src_tcp, ep_dst_udp);
	wg::tunnel::udp2tcp udp2tcp(ioc, ep_src_udp, *udp2tcp_dest_provider);

	tcp2udp.keep_alive_tcp(tcp_keep_alive);
	udp2tcp.keep_alive_tcp(tcp_keep_alive);
	udp2tcp.max_connections(max_connections);
	
	// Check for MAX_QUEUE_SIZE environment variable
	const char * env_max_queue_size = std::getenv("MAX_QUEUE_SIZE");
	if (env_max_queue_size != nullptr) {
		try {
			const size_t max_queue_size = std::stoul(env_max_queue_size);
			if (max_queue_size == 0) {
				std::cerr << PROJECT_NAME << ": MAX_QUEUE_SIZE must be greater than 0" << "\n";
				return EXIT_FAILURE;
			}
			udp2tcp.max_queue_size(max_queue_size);
		} catch (const std::exception &) {
			std::cerr << PROJECT_NAME << ": Invalid MAX_QUEUE_SIZE environment variable value" << "\n";
			return EXIT_FAILURE;
		}
	}
#if ENABLE_NGROK
	tcp2udp.keep_alive_app(ngrok_keep_alive);
	udp2tcp.keep_alive_app(ngrok_keep_alive);
#endif
#if ENABLE_TLS
	wg::utils::tls_config tls_config;
	if (tls) {
		tls_config.cert_path = tls_cert;
		tls_config.key_path = tls_key;
		tls_config.ca_path = tls_ca;
		tls_config.verify = tls_verify;
		tls_config.allow_self_signed = tls_allow_self_signed;
		tls_config.skip_verification = tls_skip_verification;
		tcp2udp.tls_config(tls_config);
		udp2tcp.tls_config(tls_config);
#if ENABLE_WEBSOCKET
		if (websocket) {
			transport = wg::utils::transport::wss;
			tcp2udp.ws_headers(websocket_headers);
			udp2tcp.ws_headers(websocket_headers);
		} else {
			transport = wg::utils::transport::tls;
		}
#else
		transport = wg::utils::transport::tls;
#endif
	}
#if ENABLE_WEBSOCKET
	else if (websocket) {
		transport = wg::utils::transport::websocket;
		tcp2udp.ws_headers(websocket_headers);
		udp2tcp.ws_headers(websocket_headers);
	}
#endif
#elif ENABLE_WEBSOCKET
	if (websocket) {
		transport = wg::utils::transport::websocket;
		tcp2udp.ws_headers(websocket_headers);
		udp2tcp.ws_headers(websocket_headers);
	}
#endif

restart:

	if (is_server)
		tcp2udp.run(transport);
	if (is_client)
		udp2tcp.run(transport);

	try {
		ioc.run();
	} catch (const std::exception & e) {
		std::cerr << PROJECT_NAME << ": " << e.what() << "\n";
		goto restart;
	}

	return EXIT_SUCCESS;
}
