package logger

import (
	"fmt"
	"io"
	"log"
	"os"

	"traffic-weir/config"
)

var Logger *log.Logger

// InitLogger initializes the logger
func InitLogger() error {
	file, err := os.OpenFile(config.LogFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return fmt.Errorf("failed to open log file: %v", err)
	}
	Logger = log.New(io.MultiWriter(os.Stdout, file), "", log.Ldate|log.Ltime|log.Lmicroseconds)
	return nil
}

// GetLogger returns the global logger instance
func GetLogger() *log.Logger {
	return Logger
}
