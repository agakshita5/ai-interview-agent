const express = require('express')
const app = express()
const server = require('http').Server(app) // create a server using express
const io = require('socket.io')(server) // create a socket.io server using the server
// const {v4 : uuidV4} = require('uuid');
// Use Node.js built-in crypto to avoid UUID ES module warning
const crypto = require('crypto');
const uuidV4 = () => crypto.randomUUID();

// import simple bot functions
const { startBot, stopBot } = require('./bot-client');

app.use(express.static('public'))
app.use(express.json())

app.set('view engine', 'ejs')
app.get('/', (req, res) =>{
    res.redirect(`/${uuidV4()}`)
})
app.get('/:room', (req,res)=>{
    res.render('room', {roomId: req.params.room})
})

// report viewing route
app.get('/report/:roomId', async (req, res) => {
    const roomId = req.params.roomId
    const axios = require('axios')
    
    try {
        // get report from Python API
        const response = await axios.get(`http://localhost:8000/agent/get-report/${roomId}`)
        const report = response.data
        
        // render report page
        res.render('report', { report: report })
    } catch (error) {
        res.render('report', { 
            report: null, 
            error: 'Report not found. Interview may still be in progress.' 
        })
    }
})

// variable to track if bot is active for a room
let activeBotRoomId = null;

io.on('connection', socket =>{
    socket.on('join-room', (roomId, userId)=>{
        console.log(roomId, userId)
        socket.join(roomId)
        socket.to(roomId).emit('user-connected', userId)
        
        // if a candidate joined, start the bot
        if (!userId.startsWith('bot-')) {
            console.log(`[Server] Candidate joined! Starting bot for room ${roomId}`)
        
            if (activeBotRoomId === null) {
                activeBotRoomId = roomId;
                startBot(roomId);
            }
        }
        
        // handle WebRTC signaling between candidate and bot
        socket.on('webrtc-offer', (data) => {
            // forward offer to bot (bot is in same room)
            socket.to(data.to).emit('webrtc-offer', {
                from: userId,
                offer: data.offer
            });
        });
        
        socket.on('webrtc-answer', (data) => {
            // forward answer to candidate
            socket.to(data.to).emit('webrtc-answer', {
                from: userId,
                answer: data.answer
            });
        });
        
        socket.on('disconnect', () => {
            console.log(`User ${userId} disconnected from room ${roomId}`)
            socket.to(roomId).emit('user-disconnected', userId)
            
            // If candidate left (not bot), stop the bot
            if (!userId.startsWith('bot-') && activeBotRoomId === roomId) {
                console.log(`[Server] Candidate left, stopping bot`)
                stopBot();
                activeBotRoomId = null;
            }
        })
    })

})

server.listen(3000, () => {
    console.log('Server running on http://localhost:3000')
    console.log('Voice Agent Bot integration is active!')
})

// When server shuts down, stop bot if it's running
process.on('SIGINT', () => {
    console.log('\n[Server] Shutting down...');
    if (activeBotRoomId !== null) {
        stopBot();
    }
    process.exit(0);
});


