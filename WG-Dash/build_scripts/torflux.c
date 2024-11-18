// Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <errno.h>
#include <sys/time.h> 


#define LOG_DIR "./log"
#define LOG_FILE LOG_DIR "/tor_circuit_refresh_log.txt"
#define BUFFER_SIZE 8192
#define TOR_CONTROL_PORT_1 9051
#define TOR_CONTROL_PORT_2 9054
#define SOCKET_TIMEOUT 5  // Timeout in seconds

// Function prototypes
void log_message(const char *message, int add_newlines, int to_console);
int send_signal(int port, const char *password, char *status_buffer);
void get_timestamp(char *buffer, size_t size);
void set_socket_timeout(int sockfd);

// Function to log messages
void log_message(const char *message, int add_newlines, int to_console) {
    FILE *log_f;
    char timestamp[64];
    get_timestamp(timestamp, sizeof(timestamp));

    // Format the log message with timestamp
    char log_message[BUFFER_SIZE];
    snprintf(log_message, BUFFER_SIZE, "[%s] %s", timestamp, message);

    // Print to console if requested
    if (to_console) {
        printf("%s\n", log_message);
    }

    // Ensure log directory exists
    mkdir(LOG_DIR, 0755);

    // Write to the log file
    log_f = fopen(LOG_FILE, "a");
    if (log_f) {
        fprintf(log_f, "%s\n", log_message);
        if (add_newlines) {
            for (int i = 0; i < 5; i++) {
                fprintf(log_f, "\n");
            }
        }
        fclose(log_f);
    } else {
        perror("[ERROR] Could not open log file");
    }
}

// Function to get current timestamp
void get_timestamp(char *buffer, size_t size) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    strftime(buffer, size, "%Y-%m-%d %H:%M:%S", t);
}

// Set a timeout for the socket
void set_socket_timeout(int sockfd) {
    struct timeval timeout;
    timeout.tv_sec = SOCKET_TIMEOUT;
    timeout.tv_usec = 0;
    setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
}

// Function to send NEWNYM signal to Tor control port
int send_signal(int port, const char *password, char *status_buffer) {
    int sockfd = -1;
    struct sockaddr_in serv_addr;
    char buffer[BUFFER_SIZE];
    int bytes_received;
    int success = 0; // Track success

    log_message("[TOR-FLUX] Sending NEWNYM signal...", 0, 0);

    // Create socket
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        log_message("[TOR-FLUX] [ERROR] Socket creation failed", 0, 0);
        return 0;
    }

    set_socket_timeout(sockfd);

    // Set up server address
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
    serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Connect to Tor control port
    if (connect(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        log_message("[TOR-FLUX] [ERROR] Connection to Tor control port failed", 0, 0);
        goto cleanup;
    }

    // Authenticate with Tor control port
    if (password && *password != '\0') {
        snprintf(buffer, sizeof(buffer), "AUTHENTICATE \"%s\"\r\n", password);
        send(sockfd, buffer, strlen(buffer), 0);
        bytes_received = recv(sockfd, buffer, sizeof(buffer), 0);
        if (bytes_received < 1 || strstr(buffer, "250") == NULL) {
            log_message("[TOR-FLUX] [ERROR] Tor authentication failed", 0, 0);
            goto cleanup;
        }
    }

    // Send NEWNYM signal
    send(sockfd, "SIGNAL NEWNYM\r\n", 15, 0);
    bytes_received = recv(sockfd, buffer, sizeof(buffer), 0);
    if (bytes_received < 1 || strstr(buffer, "250") == NULL) {
        log_message("[TOR-FLUX] [ERROR] Failed to send NEWNYM signal", 0, 0);
        goto cleanup;
    }

    // Get circuit status
    send(sockfd, "GETINFO circuit-status\r\n", 24, 0);
    bytes_received = recv(sockfd, status_buffer, BUFFER_SIZE - 1, 0);
    if (bytes_received > 0) {
        status_buffer[bytes_received] = '\0';
        success = 1;
    } else {
        status_buffer[0] = '\0';
    }

    // Log the current circuit status
    log_message("[TOR-FLUX] Current Circuit Status:", 0, 0);
    log_message(status_buffer, 0, 0);
    log_message("[TOR-FLUX] New Tor Circuits Requested Successfully.", 0, 0);

cleanup:
    if (sockfd >= 0) {
        close(sockfd);
    }
    return success;
}

int main() {
    const char *VANGUARD = getenv("VANGUARD");
    if (!VANGUARD || strlen(VANGUARD) == 0) {
        log_message("[TOR-FLUX] [ERROR] Tor control port password (VANGUARD) is not set or empty.", 0, 1);
        return 1;
    }

    log_message("[TOR-FLUX] Starting Tor circuit refresh...", 0, 1);

    // Send NEWNYM signal and get circuit statuses
    char new_status_9051[BUFFER_SIZE] = {0};
    char new_status_9054[BUFFER_SIZE] = {0};
    send_signal(TOR_CONTROL_PORT_1, VANGUARD, new_status_9051);
    send_signal(TOR_CONTROL_PORT_2, VANGUARD, new_status_9054);

    log_message("[TOR-FLUX] Tor circuit refresh completed.", 1, 1);
    return 0;
}
