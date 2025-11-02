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
        call.answer(stream) // only this will connect one peer 
        const video = document.createElement('video')
        call.on('stream', userVideoStream =>{ 
            addVideoStream(video, userVideoStream)
        })
    })

    socket.on('user-connected', userId =>{
        connectToNewUser(userId, stream)
    })
})

socket.on('user-disconnected', userId =>{
    if(peers[userId]) peers[userId].close()
})

// below code says whenever any user connects the same room execute this code; id is userid of new user
myPeer.on('open', id =>{
    socket.emit('join-room', ROOM_ID, id)
})

function addVideoStream(video, stream){
    video.srcObject = stream // this will allow to play our video
    video.addEventListener('loadedmetadata', ()=>{
        video.play()
    })
    videoGrid.append(video)
}

function connectToNewUser(userId, stream){
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