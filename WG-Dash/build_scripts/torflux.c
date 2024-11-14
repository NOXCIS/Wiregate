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

#define LOG_DIR "./log"
#define LOG_FILE LOG_DIR "/tor_circuit_refresh_log.txt"
#define BUFFER_SIZE 1024
#define TOR_CONTROL_PORT_1 9051
#define TOR_CONTROL_PORT_2 9054

// Function prototypes
void log_message(const char *message, int add_newlines, int to_console);
int send_signal(int port, const char *password, char *status_buffer);
int circuits_are_different(const char *old_status, const char *new_status);
void get_timestamp(char *buffer, size_t size);

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
    }
}

// Function to get current timestamp
void get_timestamp(char *buffer, size_t size) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    strftime(buffer, size, "%Y-%m-%d %H:%M:%S", t);
}

// Function to send NEWNYM signal to Tor control port
int send_signal(int port, const char *password, char *status_buffer) {
    int sockfd;
    struct sockaddr_in serv_addr;
    char buffer[BUFFER_SIZE];
    int bytes_received;

    log_message("[TOR] Sending NEWNYM signal...", 0, 0);

    // Create socket
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        log_message("[ERROR] Socket creation failed", 0, 0);
        return 0;
    }

    // Set up server address
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
    serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Connect to Tor control port
    if (connect(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        log_message("[ERROR] Connection to Tor control port failed", 0, 0);
        close(sockfd);
        return 0;
    }

    // Authenticate with Tor control port
    if (password != NULL) {
        snprintf(buffer, sizeof(buffer), "AUTHENTICATE \"%s\"\r\n", password);
        send(sockfd, buffer, strlen(buffer), 0);
        bytes_received = recv(sockfd, buffer, sizeof(buffer), 0);
        if (bytes_received < 1 || strstr(buffer, "250") == NULL) {
            log_message("[ERROR] Tor authentication failed", 0, 0);
            close(sockfd);
            return 0;
        }
    }

    // Send NEWNYM signal
    send(sockfd, "SIGNAL NEWNYM\r\n", 15, 0);
    bytes_received = recv(sockfd, buffer, sizeof(buffer), 0);
    if (bytes_received < 1 || strstr(buffer, "250") == NULL) {
        log_message("[ERROR] Failed to send NEWNYM signal", 0, 0);
        close(sockfd);
        return 0;
    }

    // Get circuit status
    send(sockfd, "GETINFO circuit-status\r\n", 24, 0);
    bytes_received = recv(sockfd, status_buffer, BUFFER_SIZE - 1, 0);
    if (bytes_received > 0) {
        status_buffer[bytes_received] = '\0';
    } else {
        status_buffer[0] = '\0';
    }

    // Log the current circuit status
    log_message("[TOR] Current Circuit Status:", 0, 0);
    log_message(status_buffer, 0, 0);  // Log the received circuit status

    log_message("[TOR] New Tor Circuits Requested Successfully.", 0, 0);
    close(sockfd);
    return 1;
}

// Function to check if circuits are different
int circuits_are_different(const char *old_status, const char *new_status) {
    return strcmp(old_status, new_status) != 0;
}

int main() {
    char old_status_9051[BUFFER_SIZE] = {0};
    char old_status_9054[BUFFER_SIZE] = {0};
    char new_status_9051[BUFFER_SIZE] = {0};
    char new_status_9054[BUFFER_SIZE] = {0};

    const char *VANGUARD = getenv("VANGUARD");
    if (!VANGUARD) {
        log_message("Error: Tor control port password (VANGUARD) is not set.", 0, 1);
        return 1;
    }

    log_message("Starting Tor circuit refresh...", 0, 1);

    // Get initial circuit status
    if (!send_signal(TOR_CONTROL_PORT_1, VANGUARD, old_status_9051) ||
        !send_signal(TOR_CONTROL_PORT_2, VANGUARD, old_status_9054)) {
        return 1;
    }

    // Send NEWNYM signal again and compare statuses
    send_signal(TOR_CONTROL_PORT_1, VANGUARD, new_status_9051);
    send_signal(TOR_CONTROL_PORT_2, VANGUARD, new_status_9054);

    if (circuits_are_different(old_status_9051, new_status_9051) ||
        circuits_are_different(old_status_9054, new_status_9054)) {
        log_message("Tor circuits have been successfully refreshed.", 1, 1);
    } else {
        log_message("Tor circuits did not change. Retrying...", 0, 0);
    }

    log_message("Tor circuit refresh completed.", 1, 1);
    return 0;
}
