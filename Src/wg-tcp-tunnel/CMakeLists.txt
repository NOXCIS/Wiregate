# wg-tcp-tunnel - CMakeLists.txt
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.22)

project(
	wg-tcp-tunnel
	VERSION 1.1.0
	DESCRIPTION "WireGuard TCP tunneling"
	LANGUAGES CXX)

if(WIN32)
	enable_language(CSharp)
endif()

include(GNUInstallDirs)

option(ENABLE_NGROK "Enable NGROK support" OFF)
option(ENABLE_RUNIT "Enable runit support" OFF)
option(ENABLE_SYSTEMD "Enable systemd support" OFF)
option(ENABLE_TLS "Enable TLS/SSL support" ON)
option(ENABLE_WEBSOCKET "Enable WebSocket support" OFF)

set(WGTT_RUNIT_ARGS "-U 127.0.0.1:51820 --ngrok-dst-tcp-endpoint uri=tcp:.*"
	CACHE STRING "Command line arguments used by the runit script")
set(WGTT_SYSTEMD_ARGS "-T 0.0.0.0:51820 -u 127.0.0.1:51820"
	CACHE STRING "Command line arguments used by the systemd service")

add_compile_definitions(PROJECT_NAME="${PROJECT_NAME}")
add_compile_definitions(PROJECT_VERSION="${PROJECT_VERSION}")
add_compile_definitions(ENABLE_NGROK=$<BOOL:${ENABLE_NGROK}>)
add_compile_definitions(ENABLE_SYSTEMD=$<BOOL:${ENABLE_SYSTEMD}>)
add_compile_definitions(ENABLE_TLS=$<BOOL:${ENABLE_TLS}>)
add_compile_definitions(ENABLE_WEBSOCKET=$<BOOL:${ENABLE_WEBSOCKET}>)

if(WIN32)
	# NOTE: The selected Windows version needs to match the version against
	#       which the Boost library was compiled. Otherwise, application will
	#       not link properly.
	add_compile_definitions(_WIN32_WINNT=0x0A00)
endif()

find_package(Boost 1.40.0 REQUIRED COMPONENTS log log_setup program_options)

add_executable(wg-tcp-tunnel src/main.cpp src/tcp2udp.cpp src/udp2tcp.cpp)
target_compile_features(wg-tcp-tunnel PRIVATE cxx_std_17)

target_link_libraries(wg-tcp-tunnel PRIVATE Boost::log)
target_link_libraries(wg-tcp-tunnel PRIVATE Boost::log_setup)
target_link_libraries(wg-tcp-tunnel PRIVATE Boost::program_options)

if(ENABLE_TLS OR ENABLE_NGROK)
	find_package(OpenSSL REQUIRED)
	target_link_libraries(wg-tcp-tunnel PRIVATE OpenSSL::SSL OpenSSL::Crypto)
endif()

if(ENABLE_NGROK)
	target_sources(wg-tcp-tunnel PRIVATE src/ngrok.cpp)
endif()

if(ENABLE_RUNIT)
	configure_file(
		${CMAKE_SOURCE_DIR}/misc/runit/run.in
		${CMAKE_BINARY_DIR}/misc/runit/run
		@ONLY)
	set(RUNIT_SERVICE_DIR
		"${CMAKE_INSTALL_FULL_LOCALSTATEDIR}/service/wg-tcp-tunnel")
	# Install the runit service script.
	install(PROGRAMS ${CMAKE_BINARY_DIR}/misc/runit/run
		DESTINATION ${RUNIT_SERVICE_DIR})
	# Install the symbolic link to the runit service logger.
	install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E make_directory
			${RUNIT_SERVICE_DIR}/log)")
	install(CODE "execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink
			${CMAKE_INSTALL_FULL_DATAROOTDIR}/termux-services/svlogger
			${RUNIT_SERVICE_DIR}/log/run)")
endif()

if(ENABLE_SYSTEMD)
	configure_file(
		${CMAKE_SOURCE_DIR}/misc/systemd/wg-tcp-tunnel.service.in
		${CMAKE_BINARY_DIR}/misc/systemd/wg-tcp-tunnel.service
		@ONLY)
	set(SYSTEMD_SYSTEM_DIR "${CMAKE_INSTALL_FULL_LIBDIR}/systemd/system")
	install(FILES ${CMAKE_BINARY_DIR}/misc/systemd/wg-tcp-tunnel.service
		DESTINATION ${SYSTEMD_SYSTEM_DIR})
endif()

if(WIN32)
	add_executable(
		wg-tcp-tunnel-wintray
		src/wintray.cs
		src/wintray.ico)
	set_source_files_properties(
		src/wintray.ico
		PROPERTIES
		# Embed the icon as a .NET resource
		VS_TOOL_OVERRIDE "EmbeddedResource")
	set_target_properties(
		wg-tcp-tunnel-wintray
		PROPERTIES
		VS_DOTNET_REFERENCES "Microsoft.CSharp;System;System.Core;System.Drawing;System.Windows.Forms"
		WIN32_EXECUTABLE TRUE)
endif()

install(TARGETS wg-tcp-tunnel DESTINATION ${CMAKE_INSTALL_BINDIR})
