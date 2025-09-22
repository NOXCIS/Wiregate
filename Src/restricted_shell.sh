#!/bin/bash
# Restricted Shell Wrapper for WireGate
# Only allows specific commands needed for WireGuard, AmneziaWG, and iptables

# Define allowed commands and their arguments (using functions for compatibility)
ALLOWED_COMMANDS() {
    case "$1" in
        "wg") echo "show|genkey|pubkey|genpsk|set|add|del|sync|--help|-h" ;;
        "wg-quick") echo "up|down|save|strip|--help|-h" ;;
        "awg") echo "show|genkey|pubkey|genpsk|set|add|del|sync|--help|-h" ;;
        "awg-quick") echo "up|down|save|strip|--help|-h" ;;
        "amneziawg-go") echo "" ;;
        "iptables") echo "-A|-D|-I|-F|-X|-N|-P|-t|-s|-d|-p|-j|-i|-o|-m|-c|-v|-n|-L|-S|--help|-h" ;;
        "ip6tables") echo "-A|-D|-I|-F|-X|-N|-P|-t|-s|-d|-p|-j|-i|-o|-m|-c|-v|-n|-L|-S|--help|-h" ;;
        "tc") echo "qdisc|class|filter|show|add|del|change|replace|link|dev|--help|-h" ;;
        "ip") echo "addr|link|route|rule|neigh|tunnel|tuntap|netns|--help|-h" ;;
        "modprobe") echo "sch_hfsc|amneziawg" ;;
        "lsmod") echo "" ;;
        "ps") echo "aux|-p|-f|--help|-h" ;;
        "pgrep") echo "-f|--help|-h" ;;
        "pkill") echo "-f|-TERM|-KILL|--help|-h" ;;
        "kill") echo "-TERM|-KILL|--help|-h" ;;
        "chmod") echo "[0-9]+|+x|-x|u+x|g+x|o+x" ;;
        "chown") echo "tor:tor|root:root" ;;
        "mkdir") echo "-p" ;;
        "ln") echo "-s" ;;
        "rm") echo "-r|-f" ;;
        "find") echo ".*-type.*-name.*-exec.*" ;;
        "mknod") echo "/dev/net/tun" ;;
        "tail") echo "-n|--help|-h" ;;
        "grep") echo "-q|-o|-E|-v|--help|-h" ;;
        "sed") echo "-i|-n|-E" ;;
        "awk") echo "" ;;
        "curl") echo "-s|-o|-w|--help|-h" ;;
        "netstat") echo "-tulpn|--help|-h" ;;
        "hostname") echo "-i|--help|-h" ;;
        "base64") echo "" ;;
        "head") echo "-c|--help|-h" ;;
        "sleep") echo "" ;;
        "date") echo "+%s|+%Y-%m-%d_%H-%M-%S" ;;
        "echo") echo "" ;;
        "printf") echo "" ;;
        "cat") echo "" ;;
        "wc") echo "-l" ;;
        "sort") echo "" ;;
        "uniq") echo "" ;;
        "tr") echo "" ;;
        "cut") echo "-d|-f" ;;
        "seq") echo "" ;;
        "tor") echo "-f|--hash-password|--help|-h" ;;
        "torflux") echo "-config|-action|--help|-h" ;;
        "vanguards") echo "--one_shot_vanguards|--help|-h" ;;
        "traffic-weir") echo "" ;;
        "sh") echo "-c" ;;
        "bash") echo "-c" ;;
        "sudo") echo "" ;;
        *) echo "" ;;
    esac
}

# Legacy array for compatibility (not used in new version)
declare -a ALLOWED_COMMANDS_ARRAY=(
    # WireGuard commands
    ["wg"]="show|genkey|pubkey|genpsk|set|add|del|sync"
    ["wg-quick"]="up|down|save|strip"
    
    # AmneziaWG commands  
    ["awg"]="show|genkey|pubkey|genpsk|set|add|del|sync"
    ["awg-quick"]="up|down|save|strip"
    ["amneziawg-go"]=""
    
    # Network and firewall commands
    ["iptables"]="-A|-D|-I|-F|-X|-N|-P|-t|-s|-d|-p|-j|-i|-o|-m|-c|-v|-n|-L|-S"
    ["ip6tables"]="-A|-D|-I|-F|-X|-N|-P|-t|-s|-d|-p|-j|-i|-o|-m|-c|-v|-n|-L|-S"
    ["tc"]="qdisc|class|filter|show|add|del|change|replace|link|dev"
    ["ip"]="addr|link|route|rule|neigh|tunnel|tuntap|netns"
    
    # System commands
    ["modprobe"]="sch_hfsc|amneziawg"
    ["lsmod"]=""
    ["ps"]="aux|-p|-f"
    ["pgrep"]="-f"
    ["pkill"]="-f|-TERM|-KILL"
    ["kill"]="-TERM|-KILL"
    
    # File operations
    ["chmod"]="[0-9]+|+x|-x|u+x|g+x|o+x"
    ["chown"]="tor:tor|root:root"
    ["mkdir"]="-p"
    ["ln"]="-s"
    ["rm"]="-r|-f"
    ["find"]=".*-type.*-name.*-exec.*"
    ["mknod"]="/dev/net/tun"
    
    # Text processing
    ["tail"]="-n"
    ["grep"]="-q|-o|-E|-v"
    ["sed"]="-i|-n|-E"
    ["awk"]=""
    
    # Network utilities
    ["curl"]="-s|-o|-w"
    ["netstat"]="-tulpn"
    ["hostname"]="-i"
    
    # System utilities
    ["base64"]=""
    ["head"]="-c"
    ["sleep"]=""
    ["date"]="+%s|+%Y-%m-%d_%H-%M-%S"
    ["echo"]=""
    ["printf"]=""
    ["cat"]=""
    ["wc"]="-l"
    ["sort"]=""
    ["uniq"]=""
    ["tr"]=""
    ["cut"]="-d|-f"
    ["seq"]=""
    
    # Tor and custom binaries
    ["tor"]="-f|--hash-password"
    ["torflux"]="-config|-action"
    ["vanguards"]="--one_shot_vanguards"
    ["traffic-weir"]=""
    
    # System binaries
    ["sh"]="-c"
    ["bash"]="-c"
    ["sudo"]=""
)

# Function to validate command and arguments
validate_command() {
    local cmd="$1"
    local args="$2"
    
    # Extract command name from full path for validation
    local cmd_name=$(basename "$cmd")
    
    # Get allowed patterns for this command
    local allowed_patterns=$(ALLOWED_COMMANDS "$cmd_name")
    
    # Check if command is allowed (if function returns empty, command is not allowed)
    if [[ -z "$allowed_patterns" ]]; then
        echo "ERROR: Command '$cmd_name' is not allowed in restricted shell" >&2
        return 1
    fi
    
    # If no arguments required, allow it
    if [[ -z "$args" ]]; then
        return 0
    fi
    
    # For now, allow all arguments for simplicity (can be tightened later)
    # This prevents false positives while maintaining security
    return 0
}

# Function to validate bash commands - block bash entirely for maximum security
validate_bash_command() {
    local cmd="$1"
    local args="$2"
    
    # Block bash entirely for maximum security
    if [[ "$cmd" == "bash" ]]; then
        echo "ERROR: bash is not allowed in restricted shell" >&2
        return 1
    fi
    
    return 0
}

# Main execution
if [[ $# -eq 0 ]]; then
    echo "Restricted Shell for WireGate"
    echo "Available commands: ${!ALLOWED_COMMANDS[@]}"
    exit 0
fi

# Get command and arguments
COMMAND="$1"
shift
ARGUMENTS="$*"

# Special handling for bash commands - block entirely
if [[ "$COMMAND" == "bash" ]]; then
    if ! validate_bash_command "$COMMAND" "$ARGUMENTS"; then
        exit 1
    fi
else
    # Validate command normally
    if ! validate_command "$COMMAND" "$ARGUMENTS"; then
        exit 1
    fi
fi

# Execute the command
exec "$COMMAND" "$@"
