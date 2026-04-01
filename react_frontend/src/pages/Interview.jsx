import React, { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { API, fetchJson } from "../api";

function toBase64(blob) {
    return new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onloadend = () => resolve(String(r.result).split(",")[1]);
        r.onerror = reject;
        r.readAsDataURL(blob);
    });
}

export default function Interview() {
    const location = useLocation();
    const navigate = useNavigate();
    const { roomId: roomFromNav, jdFile, candidateName = "" } = location.state || {};

    const roomIdRef = useRef(roomFromNav);
    const videoRef = useRef(null);
    const videoStreamRef = useRef(null);
    const audioStreamRef = useRef(null);
    const recRef = useRef(null);
    const chunksRef = useRef([]);
    const stopRecFn = useRef(null);

    const [status, setStatus] = useState("");
    const [showBegin, setShowBegin] = useState(true);
    const [showDone, setShowDone] = useState(false);

    useEffect(() => {
        if (!roomFromNav && !jdFile) navigate("/");
        return () => {
            try {
                recRef.current?.stop();
            } catch (e) {}
            videoStreamRef.current?.getTracks().forEach((t) => t.stop());
            audioStreamRef.current?.getTracks().forEach((t) => t.stop());
        };
    }, [roomFromNav, jdFile, navigate]);

    async function playUrl(path) {
        if (!path) return;
        const audioUrl = path.startsWith("http") ? path : `${API}${path}`;
        
        return new Promise((resolve, reject) => {
            const audio = document.createElement("audio");
            audio.crossOrigin = "anonymous";
            audio.onended = () => {
                try {
                    document.body.removeChild(audio);
                } catch (e) {}
                resolve();
            };
            audio.onerror = () => {
                try {
                    document.body.removeChild(audio);
                } catch (e) {}
                reject(new Error("Audio failed"));
            };
            audio.src = audioUrl;
            document.body.appendChild(audio);
            audio.play().catch((err) => {
                try {
                    document.body.removeChild(audio);
                } catch (e) {}
                reject(err);
            });
        });
    }

    function recordAnswer() {
        return new Promise((resolve, reject) => {
            const stream = audioStreamRef.current;
            if (!stream) {
                reject(new Error("No audio stream"));
                return;
            }
            
            const audioTracks = stream.getAudioTracks();
            if (audioTracks.length === 0) {
                reject(new Error("No audio tracks"));
                return;
            }
            
            if (audioTracks[0].readyState !== "live") {
                reject(new Error("Audio not live"));
                return;
            }

            let mime = "audio/webm";
            if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                mime = "audio/webm;codecs=opus";
            }
            
            let mr;
            try {
                mr = new MediaRecorder(stream, { mimeType: mime });
            } catch (e) {
                reject(new Error(`Create failed: ${e.message}`));
                return;
            }
            
            recRef.current = mr;
            chunksRef.current = [];
            
            mr.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };
            
            mr.onstop = () => {
                setShowDone(false);
                stopRecFn.current = null;
                if (chunksRef.current.length === 0) {
                    reject(new Error("No data"));
                    return;
                }
                resolve(new Blob(chunksRef.current, { type: mime }));
            };
            
            mr.onerror = (event) => {
                setShowDone(false);
                reject(new Error(`Error: ${event.error}`));
            };
            
            setShowDone(true);
            
            mr.start();
            
            stopRecFn.current = () => {
                if (mr && mr.state === "recording") {
                    mr.stop();
                }
            };
            
            setTimeout(() => {
                if (mr && mr.state === "recording") {
                    mr.stop();
                }
            }, 90000);
        });
    }

    async function postAudio(blob) {
        const b64 = await toBase64(blob);
        return fetchJson(`${API}/agent/process-audio`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ roomId: roomIdRef.current, audioData: b64 }),
        });
    }

    async function begin() {
        setShowBegin(false);
        try {
            let rid = roomIdRef.current;
            if (!rid && jdFile) {
                setStatus("Reading job description…");
                const fd = new FormData();
                fd.append("file", jdFile, jdFile.name);
                const res = await fetch(`${API}/agent/analyze-jd-file`, { method: "POST", body: fd });
                if (!res.ok) throw new Error("Upload failed");
                const j = await res.json();
                rid = j.roomId;
                roomIdRef.current = rid;
            }
            if (!rid) throw new Error("No session");

            setStatus("Requesting camera and microphone…");
            
            let videoStream;
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "user" },
                    audio: false,
                });
            } catch (e) {
                throw new Error("Camera access denied");
            }
            
            videoStreamRef.current = videoStream;
            if (videoRef.current) videoRef.current.srcObject = videoStream;

            setStatus("Requesting microphone…");
            
            let audioStream;
            try {
                audioStream = await navigator.mediaDevices.getUserMedia({
                    video: false,
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                });
            } catch (e) {
                videoStream.getTracks().forEach(t => t.stop());
                throw new Error("Microphone access denied");
            }
            
            audioStreamRef.current = audioStream;

            setStatus("Starting interview…");
            const start = await fetchJson(`${API}/agent/start-interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ roomId: rid, candidateName }),
            });

            setStatus("Introduction… (AI)");
            await playUrl(start.audioUrl);
            
            await new Promise(r => setTimeout(r, 1000));

            while (true) {
                setStatus("Your turn — speak, then tap Done…");
                let blob;
                try {
                    blob = await recordAnswer();
                } catch (e) {
                    setStatus(`Recording failed: ${e.message}`);
                    await new Promise(r => setTimeout(r, 2000));
                    continue;
                }

                setStatus("Response recorded…");
                await new Promise(r => setTimeout(r, 500));
                setStatus("Processing…");

                let data;
                try {
                    data = await postAudio(blob);
                } catch (e) {
                    setStatus(String(e.message || e));
                    await new Promise(r => setTimeout(r, 2000));
                    continue;
                }

                if (data.status === "no_speech") {
                    setStatus("No speech — try again.");
                    continue;
                }

                if (data.audioUrl) {
                    if (data.status === "conclusion") setStatus("Closing…");
                    else if (data.status === "followup") setStatus("Follow-up…");
                    else setStatus("Question…");
                    try {
                        await playUrl(data.audioUrl);
                    } catch (e) {
                        console.error("Audio:", e);
                    }
                    await new Promise(r => setTimeout(r, 1000));
                }

                if (data.status === "conclusion" || data.status === "done") {
                    videoStream.getTracks().forEach(x => x.stop());
                    audioStream.getTracks().forEach(x => x.stop());
                    navigate("/results", { state: { roomId: rid } });
                    return;
                }
            }
        } catch (e) {
            setStatus(String(e.message || e));
            setShowBegin(true);
        }
    }

    if (!roomFromNav && !jdFile) return null;

    return (
        <>
            <header>
                <nav>
                    <h1>AI Voice Interview</h1>
                </nav>
            </header>
            <main className="interview-main">
                <p className="interview-candidate">{candidateName}</p>
                <p className="interview-status">{status}</p>
                <div className="interview-media">
                    <video ref={videoRef} className="interview-video" autoPlay playsInline muted />
                </div>
                {showBegin ? (
                    <button type="button" className="submit-next-btn interview-begin" onClick={begin}>
                        Begin interview
                    </button>
                ) : null}
                {showDone ? (
                    <button type="button" className="submit-next-btn interview-done" onClick={() => stopRecFn.current?.()}>
                        Done speaking
                    </button>
                ) : null}
            </main>
        </>
    );
}