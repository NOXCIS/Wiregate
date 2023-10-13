import {channelSwitcher, sendMessageAddEventListener} from './messages'
import {sockets} from './sockets'

/**
 * Main TS module responsible for calling all UI-related functions after loading the app.
 */

document.addEventListener('DOMContentLoaded', () => {
    channelSwitcher()
    sendMessageAddEventListener()
    sockets()
})