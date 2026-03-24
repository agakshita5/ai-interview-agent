import React from "react";

export default function App(){
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
                            <button className="btn">Choose File</button>
                        </div>
                    </div>
                </div> 
            </main>
        </>
    )
}