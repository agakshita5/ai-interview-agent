const express = require('express')
const app = express()
const server = require('http').Server(app) // create a server using express
const io = require('socket.io')(server) // create a socket.io server using the server
// const {v4 : uuidV4} = require('uuid');
// Use Node.js built-in crypto to avoid UUID ES module warning
const crypto = require('crypto');
const uuidV4 = () => crypto.randomUUID();

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

server.listen(3000, () => {
    console.log('Server running on http://localhost:3000')
    console.log('Voice Agent Bot integration is active!')
})


