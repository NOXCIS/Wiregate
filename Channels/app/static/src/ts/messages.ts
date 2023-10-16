import {sleep} from './utils'
import {roomManager, addMessageToDB} from './sockets'
import {addChannelName} from './manage-channel'

/**
 * Module responsible for showing messages after clicking on their channel
 * and for sending a message.
 */

/** Handlebars HTML template of the message. */
const messageTemplate = require('../../handlebars/message.handlebars')

/** Number of messages displayed after loading dynamically. */
const NUM_MESSAGES = 20

/** Global variable to monitor the channel the user is currently looking at. */
let currentChannel: string

/** Global variable with the id of the next message to be dynamically loaded in a channel. */
let messageCounter: number

/**
 * JSON response of the single message.
 */
interface SingleMessage {
    readonly userName: string
    readonly userPicture: string
    readonly content: string
    readonly time: string
}

/**
 * JSON response of the get messages request to server.
 */
interface Messages {
    readonly messages: SingleMessage[]
}

interface IsAdminResponse {
    readonly response: boolean
}

/**
 * Get the initial {@link messageCounter} of the given channel.
 * @param channelName  name of the channel which initial counter the function should find.
 * @return Promise with the initial counter of the channel.
 */
function getInitialMessageCounter(channelName: string): Promise<number> {
    return new Promise<number>(resolve => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', '/initial-counter')
        xhr.responseType = 'json'

        xhr.onload = () => {
            resolve(xhr.response.counter)
        }

        const data = new FormData()
        data.append('channelName', channelName)
        xhr.send(data)
    })
}

/**
 * Get response with the messages of the given channel. Number of messages to be loaded
 * is {@link NUM_MESSAGES} and the id of the last message to be loaded is {@link messageCounter}.
 *
 * @param channelName  name of the channel which messages will be displayed.
 * @return Promise with the messages packed in JSON.
 */
function getResponseMessages(channelName: string): Promise<Messages> {
    return new Promise<Messages>(resolve => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', '/get-messages')
        xhr.responseType = 'json'
        xhr.onload = () => {
            resolve(xhr.response)
        }
        const data: FormData = new FormData()
        data.append('channelName', channelName)
        data.append('counter', messageCounter.toString())
        xhr.send(data)
    })
}

/**
 * Show input field where users can type their messages.
 */
function showInputField(): void {
    const hideSwitchChannels: NodeListOf<HTMLDivElement> = document.querySelectorAll('.hide-switch-channel')
    hideSwitchChannels.forEach(hiddenElement => {
        hiddenElement.style.display = 'block'
    })
}

/**
 * Show the title of the {@link currentChannel}.
 */
function showChannelTitle(): void {
    const channelNameInfo: HTMLElement = document.querySelector('#channel-info h3')
    channelNameInfo.innerHTML = currentChannel
}

/**
 * Scroll down to the last message.
 * @param messagesDiv  div where all messages are located.
 */
function scroll_to_last_message(messagesDiv: HTMLDivElement): void {
    messagesDiv.scrollTop = messagesDiv.scrollHeight
}

/**
 * Append a given message to the div of all messages below all current messages.
 * After appending the message, scroll down to show the message.
 *
 * @param userName  name of the user who sent that message.
 * @param userPicture  profile picture of the user.
 * @param time  time when the message was sent.
 * @param content  content of the message.
 */
export function appendMessageBottom(userName: string, userPicture: string, time: string, content: string): void {
    const messagesList: HTMLUListElement = document.querySelector('#messages-list ul')
    messagesList.innerHTML += messageTemplate({
        'userName': userName,
        'userPicture': userPicture,
        'time': time,
        'content': content
    })
    const messagesDiv = messagesList.parentElement as HTMLDivElement
    scroll_to_last_message(messagesDiv)
}

/**
 * Append a given message to the div of all messages above all current messages.
 * @param userName  name of the user who sent that message.
 * @param userPicture  profile picture of the user.
 * @param time  time when the message was sent.
 * @param content  content of the message.
 */
function appendMessageTop(userName: string, userPicture: string, time: string, content: string): void {
    const messagesList: HTMLUListElement = document.querySelector('#messages-list ul')
    messagesList.innerHTML = messageTemplate({
        'userName': userName,
        'userPicture': userPicture,
        'time': time,
        'content': content
    }) + messagesList.innerHTML
}

/**
 * Load more messages and append each of them to the messages' div.
 * Note that we need to make sure the scroll of the div is fixed.
 * Also, we need to sleep for some time to avoid loading many times at once.
 *
 * @param messagesDiv  div where all messages are located.
 */
async function loadMessagesListener(messagesDiv: HTMLDivElement): Promise<void> {
    const oldDivScrollHeight = messagesDiv.scrollHeight

    messageCounter = Math.max(messageCounter - NUM_MESSAGES, 0)
    await sleep(1500)

    const messagesResponse: Messages = await getResponseMessages(currentChannel)
    const messages: SingleMessage[] = messagesResponse.messages.reverse()
    messages.forEach(message =>
        appendMessageTop(message.userName, message.userPicture, message.time, message.content)
    )

    messagesDiv.scrollTop = messagesDiv.scrollHeight - oldDivScrollHeight
}

/**
 * Call {@link loadMessagesListener} when the user scrolled to the top of the messages' div.
 */
function loadMessagesAddEventListener(): void {
    const messagesDiv: HTMLDivElement = document.querySelector('#messages-list')
    messagesDiv.addEventListener('scroll', async () => {
        if (messagesDiv.scrollTop === 0 && messageCounter != 0) {
            await loadMessagesListener(messagesDiv)
        }
    })
}

/**
 * Show the given messages that belong to the {@link currentChannel}.
 * @param responseMessages  messages of the {@link currentChannel}.
 */
function showChannelsMessages(responseMessages: Messages): void {
    const messages: SingleMessage[] = responseMessages.messages
    const messagesList: HTMLDivElement = document.querySelector('#messages-list ul')
    messagesList.innerHTML = ''
    messages.forEach(message => appendMessageBottom(message.userName, message.userPicture, message.time, message.content))
}

function isAdmin(currentChannel: string): Promise<IsAdminResponse> {
    return new Promise<IsAdminResponse>(resolve => {
        const xhr = new XMLHttpRequest()
        xhr.open('POST', `/is-admin`)
        xhr.responseType = 'json'
        xhr.onload = () => {
            resolve(xhr.response)
        }
        const data: FormData = new FormData()
        data.append('channelName', currentChannel)
        xhr.send(data)
    })
}

function redirectManageButton(): void {
    window.location.href =
        location.protocol + '//' + document.domain + ':' + location.port + `/channel/${currentChannel}`
}

async function activateManageButton(currentChannel: string): Promise<void> {
    const admin = await isAdmin(currentChannel)
    const manageButton: HTMLButtonElement = document.querySelector('#manage-channel-btn')
    if (admin.response) {
        manageButton.style.display = 'inline'
        manageButton.disabled = false
        manageButton.addEventListener('click', redirectManageButton)
    } else {
        manageButton.style.display = 'none'
        manageButton.disabled = true
        manageButton.removeEventListener('click', redirectManageButton)
    }
}

/**
 * Change a channel and show its messages. Activate dynamic loading.
 * @param channel  channel to be switched on.
 */
function switchChannel(channel: HTMLElement): void {
    channel.addEventListener('click', async function () {
        showInputField()
        roomManager(currentChannel, this.dataset.channel)
        currentChannel = this.dataset.channel
        showChannelTitle()

        messageCounter = await getInitialMessageCounter(currentChannel)

        const responseMessages = await getResponseMessages(currentChannel)
        showChannelsMessages(responseMessages)
        loadMessagesAddEventListener()
        addChannelName(currentChannel)
        await activateManageButton(currentChannel)
    })
}

/**
 * Switch a channel and show its messages after clicking on its panel.
 */
export function channelSwitcher(): void {
    const channels: NodeListOf<HTMLDivElement> = document.querySelectorAll('.channel')
    channels.forEach(
        channel => switchChannel(channel)
    )
}

/**
 * Send the message to the {@link currentChannel}.
 * @param textArea  text area where the content of the message is.
 */
function sendMessageListener(textArea: HTMLTextAreaElement): void {
    const messageContent = textArea.value
    if (messageContent != '') {
        addMessageToDB(messageContent, currentChannel)
        textArea.value = ''
    }
}

/**
 * Send the message to the {@link currentChannel} after clicking 'send' button
 * on the website or pressing "enter".
 */
export function sendMessageAddEventListener(): void {
    const sendButton: HTMLButtonElement = document.querySelector('#messages-input-send-button')
    const textArea: HTMLTextAreaElement = document.querySelector('#messages-input-text-area')

    sendButton.addEventListener('click', () => sendMessageListener(textArea))

    textArea.addEventListener('keypress', event => {
        if (event.key === 'Enter') {
            event.preventDefault()  // prevent going to a new line
            sendMessageListener(textArea)
        }
    })
}