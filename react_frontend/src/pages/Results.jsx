import React, { useEffect, useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { API, fetchJson } from "../api";

export default function Results() {
    const location = useLocation();
    const roomId = location.state?.roomId;
    const [report, setReport] = useState(null);
    const [err, setErr] = useState("");

    useEffect(() => {
        if (!roomId) return;
        let cancelled = false;
        async function load() {
            for (let i = 0; i < 3; i++) {
                try {
                    const data = await fetchJson(`${API}/agent/get-report/${roomId}`);
                    if (!cancelled) setReport(data);
                    return;
                } catch (e) {
                    if (!cancelled) setErr(String(e.message || e));
                }
                await new Promise((r) => setTimeout(r, 1500));
            }
            if (!cancelled) setErr("Report not found yet.");
        }
        load();
        return () => {
            cancelled = true;
        };
    }, [roomId]);

    if (!roomId) {
        return (
            <>
                <header>
                    <nav>
                        <h1>AI Voice Interview</h1>
                    </nav>
                </header>
                <div className="report-shell">
                    <p className="report-error">No room. Start from the home page.</p>
                    <Link to="/" className="report-back">
                        Start new interview
                    </Link>
                </div>
            </>
        );
    }

    if (err && !report) {
        return (
            <>
                <header>
                    <nav>
                        <h1>AI Voice Interview</h1>
                    </nav>
                </header>
                <div className="report-shell">
                    <h1>Report Not Available</h1>
                    <div className="report-error">{err}</div>
                    <Link to="/" className="report-back">
                        Start new interview
                    </Link>
                </div>
            </>
        );
    }

    if (!report) {
        return (
            <>
                <header>
                    <nav>
                        <h1>AI Voice Interview</h1>
                    </nav>
                </header>
                <div className="report-shell">
                    <p>Loading report…</p>
                </div>
            </>
        );
    }

    if (report.status === "in_progress") {
        return (
            <>
                <header>
                    <nav>
                        <h1>AI Voice Interview</h1>
                    </nav>
                </header>
                <div className="report-shell">
                    <h1>Interview In Progress</h1>
                    <div className="report-error">{report.message}</div>
                    <Link to="/" className="report-back">
                        Go home
                    </Link>
                </div>
            </>
        );
    }

    const jp = report.jd_profile || {};
    const decision = (report.decision || "").toLowerCase();

    return (
        <>
            <header>
                <nav>
                    <h1>AI Voice Interview</h1>
                </nav>
            </header>
            <div className="report-shell">
                <div className="report-container">
                    <h1>Interview Report</h1>
                    <div className="report-header">
                        <div>
                            <p>
                                <strong>Candidate:</strong> {report.candidate_name}
                            </p>
                            <p>
                                <strong>Date:</strong> {report.date}
                            </p>
                            <p>
                                <strong>Room ID:</strong> {report.room_id}
                            </p>
                            {jp.role ? (
                                <p>
                                    <strong>Role:</strong> {jp.role}
                                </p>
                            ) : null}
                            {jp.skills ? (
                                <p>
                                    <strong>Skills:</strong> {jp.skills}
                                </p>
                            ) : null}
                            {jp.experience ? (
                                <p>
                                    <strong>Experience:</strong> {jp.experience}
                                </p>
                            ) : null}
                            {jp.jd_summary ? (
                                <p className="report-summary">
                                    <strong>Job summary:</strong> {jp.jd_summary}
                                </p>
                            ) : null}
                        </div>
                        <div className="report-scores">
                            <div className="report-score">{report.average_score}/4.0</div>
                            <div className={`report-decision ${decision}`}>{report.decision}</div>
                        </div>
                    </div>
                    <p className="report-meta">
                        <strong>Questions answered:</strong> {report.answered_questions} /{" "}
                        {report.total_questions}
                    </p>
                    <h2>Question Responses</h2>
                    {(report.responses || []).map((r, i) => (
                        <div className="response-item" key={i}>
                            <div className="report-question">
                                Q{i + 1}: {r.question}
                            </div>
                            <div className="report-answer">
                                <strong>Answer:</strong> {r.answer || "No answer provided"}
                            </div>
                            {r.followup_text ? (
                                <div className="report-answer">
                                    <strong>Follow-up:</strong> {r.followup_text}
                                </div>
                            ) : null}
                            {r.followup_answer ? (
                                <div className="report-answer">
                                    <strong>Follow-up answer:</strong> {r.followup_answer}
                                </div>
                            ) : null}
                            <div>
                                <span className={`rating ${r.rating.toLowerCase()}`}>{r.rating}</span>
                            </div>
                        </div>
                    ))}
                    <Link to="/" className="report-back">
                        Start new interview
                    </Link>
                </div>
            </div>
        </>
    );
}
