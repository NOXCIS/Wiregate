
  local frames=("   O   " "  \\|/  " "   |   " "  / \\  " "       ")
  local delay=0.2

  # Clear the screen
  clear

  # Loop through frames
  for frame in "${frames[@]}"; do
    # Move the cursor to the top-left corner
    tput cup 0 0

    # Print the current frame
    echo "$frame"

    # Pause for a short delay
    sleep "$delay"
  done

