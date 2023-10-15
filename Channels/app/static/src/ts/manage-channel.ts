/**
 * Add info to leave channel input about the channel that should be left.
 * @param channel_name  name of the channel to be left after clicking the "leave channel" button.
 */
export function addChannelName(channel_name: string): void {
    const leaveChannelInput: HTMLInputElement = document.querySelector('#leave-channel-input')
    leaveChannelInput.value = channel_name
}