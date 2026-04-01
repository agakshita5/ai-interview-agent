import React, {useState, useRef} from "react";
import { useNavigate } from "react-router-dom";

export default function Upload() {
    // file upload hook
    const [fileName, setFileName] = useState("");
    const [candidateName, setCandidateName] = useState("");
    const [err, setErr] = useState("");
    const fileInputRef = useRef();
    // next page hook
    const navigate = useNavigate();

    const handleFileChange = (event) => {
        if (event.target.files.length > 0) {
            setFileName(event.target.files[0].name);
            setErr("");
        }
    };

    const handleRedirect = () => {
        setErr("");
        if (!candidateName.trim()) {
            setErr("Enter your name.");
            return;
        }
        const f = fileInputRef.current?.files?.[0];
        if (!f) {
            setErr("Select a job description file.");
            return;
        }
        navigate("/interview", {
            state: {
                candidateName: candidateName.trim(),
                jdFile: f,
            },
        });
    };

    return (
        <>
            <header>
                <nav>
                    <h1>AI Voice Interview</h1>
                </nav>
            </header>
            <main>
                <div className="container">
                    <div className="upload">
                        <h2>Upload job description</h2>
                        <input
                            type="text"
                            className="upload-name"
                            value={candidateName}
                            onChange={(e) => setCandidateName(e.target.value)}
                            placeholder="Your name"
                        />
                        <div className="drop_box">
                            <h4>Select File</h4>
                            <p>Files Supported: PDF, TEXT, DOC , DOCX</p>
                            <input
                                type="file"
                                accept=".pdf,.txt,.doc,.docx"
                                style={{ display: "none" }}
                                id="file-upload-btn"
                                onChange={handleFileChange}
                                ref={fileInputRef}
                            />
                            <button
                                className="upload-btn"
                                type="button"
                                onClick={() => fileInputRef.current.click()}
                            >
                                Choose File
                            </button>
                        </div>
                        <h5>Selected file: {fileName}</h5>
                        {err ? <p className="upload-error">{err}</p> : null}
                    </div>
                    <button className="submit-next-btn" type="button" onClick={handleRedirect}>Next</button>
                </div> 
            </main>
        </>
    )
}