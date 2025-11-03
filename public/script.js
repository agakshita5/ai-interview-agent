const socket = io('/')
const videoGrid = document.getElementById('video-grid')
const myPeer = new Peer(undefined, {
    host: '/',
    port: '3001'
})
const myVideo = document.createElement('video')
myVideo.muted = true // this way our own vd is not played to us like the our voice not to us
const peers = {}

navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true
}).then(stream =>{
    addVideoStream(myVideo, stream)

    myPeer.on('call', call =>{
        call.answer(stream) // only this, will connect one peer 
        const video = document.createElement('video')
        call.on('stream', userVideoStream =>{ 
            addVideoStream(video, userVideoStream)
        })
    })

    socket.on('user-connected', userId =>{
        // if bot joined, don't show video (bot is audio-only)
        if (!isBot(userId)) {
            connectToNewUser(userId, stream)
        } else {
            console.log('Bot joined - audio only (no video)')
        }
    })
})

socket.on('user-disconnected', userId =>{
    if(peers[userId]) peers[userId].close()
})

// below code says whenever any user connects the same room execute this code; id is userid of new user
myPeer.on('open', id =>{
    socket.emit('join-room', ROOM_ID, id)
})

// end call button 
document.getElementById('end-call-btn').addEventListener('click', () => {
    // close all peer connections
    Object.values(peers).forEach(peer => peer.close())
    
    // stop local video/audio stream
    if (myVideo.srcObject) {
        myVideo.srcObject.getTracks().forEach(track => track.stop())
    }
    
    // disconnect socket
    socket.disconnect()
    
    // redirect to home or show report
    window.location.href = `/report/${ROOM_ID}`
})

function addVideoStream(video, stream){
    video.srcObject = stream // this will allow to play our video
    video.addEventListener('loadedmetadata', ()=>{
        video.play()
    })
    videoGrid.append(video)
}

// hide bot video - bot doesn't need video, only audio
function isBot(userId) {
    return userId && userId.startsWith('bot-');
}

function connectToNewUser(userId, stream){
    // don't connect to bot via PeerJS (bot uses different connection method)
    if (isBot(userId)) {
        console.log('Skipping PeerJS connection with bot - bot uses WebRTC signaling')
        return;
    }
    
    const call = myPeer.call(userId, stream) // via peer we are connecting to new user using userId and sending it stream (audio/video)
    const video = document.createElement('video')
    call.on('stream', userVideoStream =>{ // user sending back its video stream when connected
        addVideoStream(video, userVideoStream)
    })
    call.on('close', () =>{ // remove video from screen when browser/tab closed
        video.remove()
    })

    peers[userId] = call
}   