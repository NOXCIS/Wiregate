# WireGate Makefile for bare metal build
SHELL := /bin/bash

# Directories
PREFIX ?= ../
INSTALL_DIR ?= $(PREFIX)/WireGate_Built
WIREGATE_SRC = .
BUILD_DIR = ./build
TOR_PLUGINS_DIR = /usr/local/bin
STATIC_DIR = $(WIREGATE_SRC)/static/app
STATIC_DIR_LOCALE = $(WIREGATE_SRC)/static

AWG_GO_DIR = /usr/bin

# Go settings
GO_VERSION = 1.24.0
GO_ARCH ?= $(shell uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
GO_LDFLAGS = -X main.version=v1.0.0 -s -w

# Add Tor pluggable transports targets
.PHONY: all install clean deps frontend go-deps python-deps go-bins py-bins lyrebird snowflake webtunnel tor-plugins builder-deps

# Update the 'all' target to include tor-plugins
all: deps frontend go-bins py-bins tor-plugins

# Install dependencies
deps: builder-deps frontend-deps go-deps amneziawg-deps python-deps 

amneziawg-deps:
	mkdir -p $(BUILD_DIR)/amneziawg-tools $(BUILD_DIR)/amneziawg-go
	
	# Clone or update repositories
	if [ ! -d "amneziawg-tools" ]; then \
		git clone --depth=1 https://github.com/amnezia-vpn/amneziawg-tools.git $(BUILD_DIR)/amneziawg-tools; \
	else \
		echo "amneziawg-tools directory exists, copying to build directory"; \
		cp -r amneziawg-tools/* $(BUILD_DIR)/amneziawg-tools/; \
		cd $(BUILD_DIR)/amneziawg-tools && git pull; \
	fi
	
	if [ ! -d "amneziawg-go" ]; then \
		git clone --depth=1 https://github.com/amnezia-vpn/amneziawg-go.git $(BUILD_DIR)/amneziawg-go; \
	else \
		echo "amneziawg-go directory exists, copying to build directory"; \
		cp -r amneziawg-go/* $(BUILD_DIR)/amneziawg-go/; \
		cd $(BUILD_DIR)/amneziawg-go && git pull; \
	fi
	
	# Using a single shell context for all commands to maintain environment variables
	export PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" && \
	echo "Using Go: $$(go version)" && \
	cd $(BUILD_DIR)/amneziawg-tools/src && make && \
	cd ../../amneziawg-go && \
	go get -u ./... && \
	go mod tidy && \
	make && \
	chmod +x amneziawg-go ../amneziawg-tools/src/wg ../amneziawg-tools/src/wg-quick/linux.bash
	@echo "DONE AmneziaWG"

# Add to the top with other variables
NODE_VERSION = 20.11.1
NODE_DIST_DIR = $(BUILD_DIR)/node
NODE_INSTALL_DIR = $(BUILD_DIR)/node-install

builder-deps:
	# Install Node.js and npm in build directory
	mkdir -p $(NODE_DIST_DIR) $(NODE_INSTALL_DIR)
	
	if [ ! -f "$(NODE_INSTALL_DIR)/bin/node" ]; then \
		curl -o $(NODE_DIST_DIR)/node.tar.gz https://nodejs.org/dist/v$(NODE_VERSION)/node-v$(NODE_VERSION).tar.gz && \
		tar -xzf $(NODE_DIST_DIR)/node.tar.gz -C $(NODE_DIST_DIR) --strip-components=1 && \
		cd $(NODE_DIST_DIR) && \
		./configure --prefix=$(abspath $(NODE_INSTALL_DIR)) && \
		make -j$(nproc) && \
		make install && \
		cd .. && \
		rm -rf $(NODE_DIST_DIR)/* ; \
	fi

	# Add source language download mirrors
	PIP_MIRRORS="https://pypi.tuna.tsinghua.edu.cn/simple \
		https://mirrors.aliyun.com/pypi/simple \
		https://pypi.org/simple"

	NPM_MIRRORS="https://registry.npmmirror.com \
		https://registry.npmjs.org"

	# Install other build dependencies
	if grep -q "Alpine" /etc/os-release 2>/dev/null; then \
		apk add --no-cache python3 py3-virtualenv py3-pip musl-dev build-base zlib-dev libffi-dev openssl-dev linux-headers rust cargo wget; \
	elif grep -q "Debian\|Ubuntu\|Mint" /etc/os-release 2>/dev/null; then \
		apt-get update && apt-get install -y python3 python3-venv python3-pip build-essential zlib1g-dev libffi-dev libssl-dev linux-headers-generic rustc cargo wget; \
	elif grep -q "Arch\|Manjaro" /etc/os-release 2>/dev/null; then \
		pacman -Sy --noconfirm python python-virtualenv python-pip base-devel zlib libffi openssl linux-headers rust cargo wget; \
	elif grep -q "Fedora" /etc/os-release 2>/dev/null; then \
		dnf install -y python3 python3-virtualenv python3-pip gcc gcc-c++ make zlib-devel libffi-devel openssl-devel kernel-headers rust cargo wget; \
	elif grep -q "SUSE" /etc/os-release 2>/dev/null; then \
		zypper install -y python3 python3-virtualenv python3-pip gcc gcc-c++ make zlib-devel libffi-devel libopenssl-devel kernel-headers rust cargo wget; \
	elif grep -q "CentOS\|RHEL" /etc/os-release 2>/dev/null; then \
		yum install -y python3 python3-virtualenv python3-pip gcc gcc-c++ make zlib-devel libffi-devel openssl-devel kernel-headers rust cargo wget; \
	else \
		echo "WARNING: Unsupported distribution. Please install dependencies manually."; \
	fi

	# Configure pip to use mirrors
	mkdir -p ~/.pip && \
	echo "[global]" > ~/.pip/pip.conf && \
	echo "index-url = $(word 1,$(PIP_MIRRORS))" >> ~/.pip/pip.conf && \
	echo "extra-index-url = $(wordlist 2,$(words $(PIP_MIRRORS)),$(PIP_MIRRORS))" >> ~/.pip/pip.conf

	# Configure npm to use mirrors (using local npm installation)
	$(NODE_INSTALL_DIR)/bin/npm config set registry $(word 1,$(NPM_MIRRORS)) && \
	$(NODE_INSTALL_DIR)/bin/npm config set disturl $(word 1,$(NPM_MIRRORS))/dist

# Frontend dependencies and build
frontend-deps:
	@echo "Installing Node.js dependencies..."
	cd $(STATIC_DIR) && \
	# Clear existing node_modules and package-lock.json for clean install
	rm -rf node_modules package-lock.json && \
	# Use configured npm with mirrors
	$(NODE_INSTALL_DIR)/bin/npm cache clean --force && \
	$(NODE_INSTALL_DIR)/bin/npm install --no-audit --no-fund

frontend: frontend-deps
	@echo "Building frontend..."
	cd $(STATIC_DIR) && \
	$(NODE_INSTALL_DIR)/bin/npm run build && \
	mkdir -p $(BUILD_DIR)/app && \
	mv dist $(BUILD_DIR)/app/dist && \
	# Clean up node_modules after build
	rm -rf node_modules

# Go dependencies
go-deps:
	@echo "Setting up Go environment..."
	mkdir -p $(BUILD_DIR)/go
	if ! command -v go > /dev/null; then \
		echo "Installing Go $(GO_VERSION)..."; \
		wget -q https://golang.org/dl/go$(GO_VERSION).linux-$(GO_ARCH).tar.gz; \
		tar -C $(BUILD_DIR) -xzf go$(GO_VERSION).linux-$(GO_ARCH).tar.gz; \
		rm go$(GO_VERSION).linux-$(GO_ARCH).tar.gz; \
		export PATH="$(BUILD_DIR)/go/bin:$$PATH"; \
	fi

# Python dependencies
python-deps:
	@echo "Installing Python dependencies..."
	python3 -m venv $(BUILD_DIR)/venv
	$(BUILD_DIR)/venv/bin/pip install --upgrade pip
	$(BUILD_DIR)/venv/bin/pip install -r $(WIREGATE_SRC)/requirements.txt
	$(BUILD_DIR)/venv/bin/pip install pyinstaller

# Build Go binaries
go-bins: go-deps
	@echo "Building Go binaries..."
	mkdir -p $(BUILD_DIR)/torflux-build $(BUILD_DIR)/traffic_weir
	
	# Copy Go source files
	cp ./torflux/torflux.go $(BUILD_DIR)/torflux-build/
	cp ./torflux/go.mod $(BUILD_DIR)/torflux-build/
	cp ./traffic_weir/traffic-weir.go $(BUILD_DIR)/traffic_weir/
	cp ./traffic_weir/pf_helper.go $(BUILD_DIR)/traffic_weir/
	cp ./traffic_weir/go.mod $(BUILD_DIR)/traffic_weir/
	
	# Build torflux
	cd $(BUILD_DIR)/torflux-build && \
		export PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" && \
		GOOS=linux GOARCH=$(GO_ARCH) CGO_ENABLED=0 go build \
		-ldflags="$(GO_LDFLAGS)" \
		-buildvcs=false \
		-o ../torflux
	
	# Build traffic-weir
	cd $(BUILD_DIR)/traffic_weir && \
		export PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" && \
		GOOS=linux GOARCH=$(GO_ARCH) CGO_ENABLED=0 go build \
		-ldflags="$(GO_LDFLAGS)" \
		-buildvcs=false \
		-o ../traffic-weir

# Build Python binaries
py-bins: python-deps
	@echo "Building Python binaries with PyInstaller..."
	mkdir -p $(BUILD_DIR)/dist
	mkdir -p $(BUILD_DIR)/wiregate
	mkdir -p $(BUILD_DIR)/vanguards
	
	# Copy Python source files
	cp -r $(WIREGATE_SRC)/wiregate/* $(BUILD_DIR)/wiregate/
	cp $(WIREGATE_SRC)/wiregate.py $(BUILD_DIR)/
	cp -r $(WIREGATE_SRC)/vanguards/* $(BUILD_DIR)/vanguards/
	cp $(WIREGATE_SRC)/vanguards.py $(BUILD_DIR)/
	
	# Build wiregate binary
	cd $(BUILD_DIR) && \
		$(abspath $(BUILD_DIR))/venv/bin/pyinstaller \
		--onefile \
		--clean \
		--hidden-import=gunicorn.glogging \
		--hidden-import=gunicorn.workers.sync \
		--hidden-import=gunicorn.workers.gthread \
		--distpath=$(abspath $(BUILD_DIR))/dist \
		--name=wiregate \
		wiregate.py
	
	# Build vanguards binary
	cd $(BUILD_DIR) && \
		$(abspath $(BUILD_DIR))/venv/bin/pyinstaller \
		--onefile \
		--clean \
		--distpath=$(abspath $(BUILD_DIR))/dist \
		--name=vanguards \
		vanguards.py

# Tor pluggable transports
tor-plugins: lyrebird snowflake webtunnel

# Build lyrebird (obfs4)
lyrebird: go-deps
	@echo "Building lyrebird (obfs4)..."
	mkdir -p $(BUILD_DIR)
	git clone --depth=1 https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/lyrebird.git $(BUILD_DIR)/lyrebird
	cd $(BUILD_DIR)/lyrebird && \
	PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" \
	VERSION=$$(git describe --tags 2>/dev/null | sed 's/lyrebird-//' || echo "dev") \
	GOOS=linux GOARCH=$(GO_ARCH) CGO_ENABLED=0 \
	go build -ldflags="-X main.lyrebirdVersion=$$VERSION" ./cmd/lyrebird
	chmod +x $(BUILD_DIR)/lyrebird/lyrebird
	@echo "DONE LYREBIRD AKA OBFS4"

# Build snowflake
snowflake: go-deps
	@echo "Building snowflake..."
	mkdir -p $(BUILD_DIR)
	git clone --depth=1 https://git.torproject.org/pluggable-transports/snowflake.git $(BUILD_DIR)/snowflake
	cd $(BUILD_DIR)/snowflake/client && \
	PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" \
	GOOS=linux GOARCH=$(GO_ARCH) CGO_ENABLED=0 \
	go build -a -installsuffix cgo -ldflags="-s -w"
	chmod +x $(BUILD_DIR)/snowflake/client/client
	@echo "DONE SNOWFLAKE"

# Build webtunnel
webtunnel: go-deps
	@echo "Building webtunnel..."
	mkdir -p $(BUILD_DIR)
	git clone --depth=1 https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/webtunnel.git $(BUILD_DIR)/webtunnel
	cd $(BUILD_DIR)/webtunnel/main/client && \
	PATH="$(abspath $(BUILD_DIR))/go/bin:$$PATH" \
	GOOS=linux GOARCH=$(GO_ARCH) CGO_ENABLED=0 \
	go build -a -installsuffix cgo -ldflags="-s -w"
	chmod +x $(BUILD_DIR)/webtunnel/main/client/client
	@echo "DONE WEBTUNNEL"

# Install everything
install: all
	@echo "Installing WireGate to $(INSTALL_DIR)..."
	
	# Create installation directories
	mkdir -p $(INSTALL_DIR)
	mkdir -p $(INSTALL_DIR)/db
	mkdir -p $(INSTALL_DIR)/log
	mkdir -p $(INSTALL_DIR)/static/app/dist
	mkdir -p $(INSTALL_DIR)/static/locale
	mkdir -p $(INSTALL_DIR)/iptable-rules
	mkdir -p $(INSTALL_DIR)/dnscrypt
	mkdir -p $(INSTALL_DIR)/SSL_CERT
	mkdir -p /usr/local/bin
	
	# Create Tor user if it doesn't exist
	@echo "Creating Tor user if it doesn't exist..."
	if ! id -u tor &>/dev/null; then \
		if command -v adduser &>/dev/null && grep -q "Alpine" /etc/os-release 2>/dev/null; then \
			# Alpine Linux \
			adduser -S -D -H -s /sbin/nologin tor; \
		elif command -v adduser &>/dev/null && grep -q "Arch\|Manjaro" /etc/os-release 2>/dev/null; then \
			# Arch Linux / Manjaro \
			adduser -S -D -H -s /bin/false tor; \
		elif command -v adduser &>/dev/null && grep -q "Debian\|Ubuntu\|Mint" /etc/os-release 2>/dev/null; then \
			# Debian / Ubuntu / Mint \
			adduser --system --no-create-home --disabled-login --group tor; \
		elif command -v useradd &>/dev/null; then \
			# RHEL / CentOS / Fedora / SUSE / Generic Linux \
			useradd --system --no-create-home --shell /bin/false tor; \
		else \
			echo "WARNING: Could not create tor user. Please create it manually."; \
		fi; \
	fi
	
	
	


	# Copy frontend assets
	cp -r $(BUILD_DIR)/app/dist/* $(INSTALL_DIR)/static/app/dist/
	cp $(STATIC_DIR)/index.html $(INSTALL_DIR)/static/app/
	cp -r $(STATIC_DIR)/public $(INSTALL_DIR)/static/app/
	cp -r $(STATIC_DIR_LOCALE)/locale $(INSTALL_DIR)/static/
	# Copy binaries
	cp $(BUILD_DIR)/dist/wiregate $(INSTALL_DIR)/
	cp $(BUILD_DIR)/dist/vanguards $(INSTALL_DIR)/
	cp $(BUILD_DIR)/torflux $(INSTALL_DIR)/
	cp $(BUILD_DIR)/traffic-weir $(INSTALL_DIR)/
	# Copy wiregate.sh
	cp $(WIREGATE_SRC)/wiregate.sh $(INSTALL_DIR)/
	cp $(WIREGATE_SRC)/db/wsgi.ini $(INSTALL_DIR)/db/
	cp -r $(WIREGATE_SRC)/iptable-rules $(INSTALL_DIR)/

	cp -r $(WIREGATE_SRC)/dnscrypt $(INSTALL_DIR)/dnscrypt
	
	# Copy Tor pluggable transports
	cp $(BUILD_DIR)/lyrebird/lyrebird $(TOR_PLUGINS_DIR)/obfs4
	cp $(BUILD_DIR)/snowflake/client/client $(TOR_PLUGINS_DIR)/snowflake
	cp $(BUILD_DIR)/webtunnel/main/client/client $(TOR_PLUGINS_DIR)/webtunnel

	cp $(BUILD_DIR)/amneziawg-go/amneziawg-go $(AWG_GO_DIR)/amneziawg-go
	cp $(BUILD_DIR)/amneziawg-tools/src/wg $(AWG_GO_DIR)/awg
	cp $(BUILD_DIR)/amneziawg-tools/src/wg-quick/linux.bash $(AWG_GO_DIR)/awg-quick

	chmod +x $(AWG_GO_DIR)/amneziawg-go
	chmod +x $(AWG_GO_DIR)/awg
	chmod +x $(AWG_GO_DIR)/awg-quick

	chmod +x $(TOR_PLUGINS_DIR)/obfs4
	chmod +x $(TOR_PLUGINS_DIR)/snowflake
	chmod +x $(TOR_PLUGINS_DIR)/webtunnel
	
	chmod +x $(INSTALL_DIR)/wiregate
	chmod +x $(INSTALL_DIR)/vanguards
	chmod +x $(INSTALL_DIR)/torflux
	chmod +x $(INSTALL_DIR)/traffic-weir
	chmod +x $(INSTALL_DIR)/wiregate.sh
	
	
	# Create symlinks to binaries
	#ln -sf $(INSTALL_DIR)/wiregate /usr/local/bin/wiregate
	#ln -sf $(INSTALL_DIR)/vanguards /usr/local/bin/vanguards
	#ln -sf $(INSTALL_DIR)/torflux /usr/local/bin/torflux
	#ln -sf $(INSTALL_DIR)/traffic-weir /usr/local/bin/traffic-weir
	
	# Create and set ownership for Tor directories
	mkdir -p /var/lib/tor /var/log/tor
	chown -R tor:tor /var/lib/tor/
	chown -R tor:tor /var/log/tor/
	chmod 700 /var/lib/tor/
	chmod 700 /var/log/tor/



	@echo "Installation complete. You may need to install additional system packages:"
	@echo "- wireguard-tools"
	@echo "- amneziawg linux kernel module"
	@echo "- iptables"
	@echo "- ip6tables"
	@echo "- tzdata"
	@echo "- sudo"
	
	
	
	@echo "For AmneziaWG kernel level support, install the amnesia-wg kernel module"
	
	@echo "Tor pluggable transports have been built and installed in $(INSTALL_DIR)/tor-plugins/"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf $(STATIC_DIR)/node_modules
	rm -rf $(STATIC_DIR)/dist

