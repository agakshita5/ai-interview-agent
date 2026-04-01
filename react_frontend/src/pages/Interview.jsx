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
        const a = new Audio(path.startsWith("http") ? path : `${API}${path}`);
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
                reject(new Error("No mic"));
                return;
            }
            let mime = "audio/webm;codecs=opus";
            if (!MediaRecorder.isTypeSupported(mime)) mime = "audio/webm";
            const mr = MediaRecorder.isTypeSupported(mime)
                ? new MediaRecorder(stream, { mimeType: mime })
                : new MediaRecorder(stream);
            recRef.current = mr;
            chunksRef.current = [];
            mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
            mr.onstop = () => {
                setShowDone(false);
                stopRecFn.current = null;
                clearTimeout(tmax);
                resolve(new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" }));
            };
            mr.onerror = () => reject(new Error("recorder"));
            mr.start(200);
            setShowDone(true);
            stopRecFn.current = () => {
                if (mr.state === "recording") mr.stop();
            };
            const tmax = setTimeout(() => {
                if (mr.state === "recording") mr.stop();
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
                const j = await fetchJson(`${API}/agent/analyze-jd-file`, { method: "POST", body: fd });
                rid = j.roomId;
                roomIdRef.current = rid;
            }
            if (!rid) throw new Error("no session");

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" },
                audio: true,
            });
            streamRef.current = stream;
            if (videoRef.current) videoRef.current.srcObject = stream;

            const start = await fetchJson(`${API}/agent/start-interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ roomId: rid, candidateName }),
            });

            setStatus("Introduction… (AI)");
            await playUrl(start.audioUrl);

            while (true) {
                setStatus("Your turn — speak, then tap Done…");
                const blob = await recordAnswer();

                setStatus("Response recorded…");
                await new Promise((r) => setTimeout(r, 400));
                setStatus("Processing…");

                let data;
                try {
                    data = await postAudio(blob);
                } catch (e) {
                    setStatus(String(e.message || e));
                    return;
                }

                if (data.status === "no_speech") {
                    setStatus("No speech detected — try again. (you)");
                    continue;
                }

                if (data.audioUrl) {
                    if (data.status === "conclusion") setStatus("Closing… (AI)");
                    else if (data.status === "followup") setStatus("Follow-up… (AI)");
                    else setStatus("Question asked… (AI)");
                    try {
                        await playUrl(data.audioUrl);
                    } catch (e) {}
                }

                if (data.status === "conclusion" || data.status === "done") {
                    stream.getTracks().forEach((x) => x.stop());
                    navigate("/results", { state: { roomId: rid } });
                    return;
                }
            }
        } catch (e) {
            setStatus(String(e.message || e));
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