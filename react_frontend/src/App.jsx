import React, {useState, useRef} from "react";

export default function App(){
    const [fileName, setFileName] = useState("");
    const fileInputRef = useRef()
	const handleFileChange = (event) => {
		if (event.target.files.length > 0) {
			setFileName(event.target.files[0].name);
		}
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
                        <h2>Upload Resume</h2>
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
                                onClick={() => fileInputRef.current.click()}
                            >Choose File</button>
                        </div>
                        <h5>Selected file: {fileName}</h5>
                    </div>
                </div> 
            </main>
        </>
    )
}