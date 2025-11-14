const API_BASE = "";
let mediaRecorder;
let currentRoomId = ROOM_ID;
let currentQuesIdx = 0; // for 1st ques
let interviewActive = false;
const startBtn = document.getElementById("startBtn");
const recordBtn = document.getElementById("recordBtn");
const endBtn = document.getElementById("endBtn");
const logBox = document.getElementById("log");
const selfVideo = document.getElementById("selfVideo");

function log(msg) {
    console.log(msg);
    logBox.innerHTML += `<div>• ${msg}</div>`;
}

startBtn.addEventListener("click", async () => {
    interviewActive = true;
    const camStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    selfVideo.srcObject = camStream;
    const name = prompt("Enter your name to begin:");
    if (!name) return;

    log("Starting interview...");
    const res = await fetch(`${API_BASE}/agent/start-interview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomId: currentRoomId, candidateName: name }),
    });
    const data = await res.json();
    log("Interview started. Playing intro...");
    await playBotAudio(`${API_BASE}${data.audioUrl}`);
    
    recordBtn.disabled = false;
    endBtn.disabled = false;

    log("Intro finished. Asking first question...");
    const qres = await fetch(`${API_BASE}/agent/next-question`, { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomId: currentRoomId }),
     });
    const qdata = await qres.json();
    await playBotAudio(`${API_BASE}${qdata.audioUrl}`);
    log("Bot asked first question. Starting to record...");
    recordBtn.click();  // automatically start recording after bot speaks
});

recordBtn.addEventListener("click", async () => {
    log("Recording your answer...");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    source.connect(analyser);

    const dataArray = new Uint8Array(analyser.fftSize);
    const SILENCE_THRESHOLD = 0.02; 
    const MAX_SILENCE_TIME = 3000; 

    let silenceStart = null;
    let recordingStarted = false;
    let audioChunks = [];

    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        log("Recording stopped. Sending to server...");
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const base64 = await blobToBase64(audioBlob);

        const res = await fetch(`${API_BASE}/agent/process-audio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomId: currentRoomId, audioData: base64 }),
        });

        const data = await res.json();
        log("Server processed your answer.");

        if (data.audioUrl) {
            await playBotAudio(`${API_BASE}${data.audioUrl}`);
            if (!interviewActive) return;
            log("Bot responded with next question/followup.");
            recordBtn.click();
        } else {
            log("No more bot audio. Check report soon.");
        }

        if (data.status === "done" || data.reportReady) {
        log("Interview finished. Generating report...");
        endInterview();
        }
    };

    mediaRecorder.start();

    const detectSilence = () => {
        analyser.getByteTimeDomainData(dataArray); // dataArray is audio waveform as 8-bit int(0-255)
        const normalized = dataArray.map(v => (v - 128) / 128); // silence is 128 (range's middle) | sound -> 100,150,..
        // root mean square of auio samples in current frame -> small when silence and large while speaking
        // converts live mic signal into a single number telling how “loud” it is on average -> which helps in detecting silence or speaking
        const rms = Math.sqrt(normalized.reduce((sum, v) => sum + v * v, 0) / normalized.length);
    
        if (rms > SILENCE_THRESHOLD) {
          recordingStarted = true;
          silenceStart = null;
        } else if (recordingStarted) {
          if (!silenceStart) silenceStart = performance.now();
          if (performance.now() - silenceStart > MAX_SILENCE_TIME) {
            log("Silence detected. Auto-stopping...");
            mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
            return; // exit loop
          }
        }
    
        requestAnimationFrame(detectSilence);
    };

    detectSilence();

    setTimeout(() => {
        if (mediaRecorder.state !== "inactive") {
            log("Timeout reached. Auto-stopping...");
            mediaRecorder.stop();
            stream.getTracks().forEach(t => t.stop());
        }
    }, 15000); 
});

endBtn.addEventListener("click", async () => {
    await endInterview();
});

async function endInterview() {
    interviewActive = false;
    log("Fetching report...");
    try {
        const response = await fetch(`/agent/get-report/${currentRoomId}`);
        const data = await response.json();

        if (data.status === "in_progress") {
            log("Interview still in progress. Redirecting to report page...");
        } else {
            log("Final report generated. Redirecting to report page...");
        }

        window.location.href = `/report/${currentRoomId}`;
    } catch (err) {
        console.error("Error getting report:", err);
        log("Error getting report.");
    }
}

async function playBotAudio(url) {
    return new Promise((resolve, reject) => {
        const audio = new Audio(url);
        audio.onended = () => resolve(); // resolves when bot finishes speaking
        audio.onerror = (err) => reject(err);
        audio.play();
    });
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
        const base64data = reader.result.split(",")[1];
        resolve(base64data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}
