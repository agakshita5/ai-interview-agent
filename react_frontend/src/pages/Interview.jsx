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
    const streamRef = useRef(null);
    const audioContextRef = useRef(null);
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
            streamRef.current?.getTracks().forEach((t) => t.stop());
        };
    }, [roomFromNav, jdFile, navigate]);

    async function playUrl(path) {
        if (!path) return;
        const audioUrl = path.startsWith("http") ? path : `${API}${path}`;
        const a = new Audio(audioUrl);
        a.crossOrigin = "anonymous";
        await new Promise((res, rej) => {
            a.onended = res;
            a.onerror = rej;
            a.play().catch(rej);
        });
    }

    function recordAnswer() {
        return new Promise((resolve, reject) => {
            const stream = streamRef.current;
            if (!stream) {
                reject(new Error("Stream lost. Refresh and try again."));
                return;
            }
            
            const audioTracks = stream.getAudioTracks();
            if (!audioTracks || audioTracks.length === 0) {
                reject(new Error("No audio track available"));
                return;
            }
            
            if (audioTracks[0].readyState !== "live") {
                reject(new Error("Audio track not live. Checking..."));
                return;
            }

            let mime = "audio/webm";
            if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                mime = "audio/webm;codecs=opus";
            }
            
            let mr;
            try {
                const options = { 
                    mimeType: mime,
                    audioBitsPerSecond: 128000 
                };
                mr = new MediaRecorder(stream, options);
            } catch (e) {
                reject(new Error(`MediaRecorder creation failed: ${e.message}`));
                return;
            }
            
            recRef.current = mr;
            chunksRef.current = [];
            let hasData = false;
            
            mr.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    hasData = true;
                    chunksRef.current.push(e.data);
                }
            };
            
            mr.onstop = () => {
                setShowDone(false);
                stopRecFn.current = null;
                clearTimeout(tmax);
                if (!hasData || chunksRef.current.length === 0) {
                    reject(new Error("No audio data captured"));
                    return;
                }
                resolve(new Blob(chunksRef.current, { type: mime }));
            };
            
            mr.onerror = (event) => {
                reject(new Error(`Recorder error: ${event.error?.name || 'unknown'}`));
            };
            
            setShowDone(true);
            
            try {
                mr.start();
            } catch (startErr) {
                reject(new Error(`Cannot start recording: ${startErr.message}`));
                setShowDone(false);
                return;
            }
            
            stopRecFn.current = () => {
                try {
                    if (mr && mr.state === "recording") {
                        mr.stop();
                    }
                } catch (e) {
                    console.error("Error stopping recorder:", e);
                }
            };
            
            const tmax = setTimeout(() => {
                try {
                    if (mr && mr.state === "recording") {
                        mr.stop();
                    }
                } catch (e) {}
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
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || `Upload failed (${res.status})`);
                }
                const j = await res.json();
                rid = j.roomId;
                roomIdRef.current = rid;
            }
            if (!rid) throw new Error("no session");

            setStatus("Requesting microphone…");
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "user" },
                    audio: {
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: true
                    },
                });
            } catch (e) {
                throw new Error(`Microphone denied. Check browser permissions.`);
            }
            
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }

            setStatus("Fetching interview intro…");
            const start = await fetchJson(`${API}/agent/start-interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ roomId: rid, candidateName }),
            });

            setStatus("Introduction… (AI)");
            await playUrl(start.audioUrl);
            
            await new Promise(r => setTimeout(r, 500));

            while (true) {
                setStatus("Your turn — speak, then tap Done…");
                let blob;
                try {
                    blob = await recordAnswer();
                } catch (e) {
                    setStatus(`Recording error: ${e.message}`);
                    await new Promise(r => setTimeout(r, 1500));
                    continue;
                }

                setStatus("Response recorded…");
                await new Promise((r) => setTimeout(r, 300));
                setStatus("Processing…");

                let data;
                try {
                    data = await postAudio(blob);
                } catch (e) {
                    setStatus(String(e.message || e));
                    await new Promise(r => setTimeout(r, 1500));
                    continue;
                }

                if (data.status === "no_speech") {
                    setStatus("No speech detected — try again.");
                    continue;
                }

                if (data.audioUrl) {
                    if (data.status === "conclusion") setStatus("Closing… (AI)");
                    else if (data.status === "followup") setStatus("Follow-up… (AI)");
                    else setStatus("Question… (AI)");
                    try {
                        await playUrl(data.audioUrl);
                    } catch (e) {
                        console.error("Audio playback error:", e);
                    }
                    await new Promise(r => setTimeout(r, 300));
                }

                if (data.status === "conclusion" || data.status === "done") {
                    stream.getTracks().forEach((x) => x.stop());
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