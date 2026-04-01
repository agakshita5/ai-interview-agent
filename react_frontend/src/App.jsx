import React from "react";
import Upload from "./pages/Upload"; 
import Interview from "./pages/Interview";
import Results from "./pages/Results"
import { BrowserRouter as Router, Routes, Route} from "react-router-dom"

export default function App(){
    return (
        <Router>
            <Routes>
                <Route
                    path="/"
                    element={<Upload />}
                />
                <Route
                    path="/interview"
                    element={<Interview />}
                />
                <Route
                    path="/results"
                    element={<Results />}
                />
            </Routes>
        </Router>
    )
}