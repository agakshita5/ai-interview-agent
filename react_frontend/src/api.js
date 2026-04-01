export const API = process.env.REACT_APP_API_URL || "";

function tryParseJson(text) {
    if (!text) return null;
    try {
        return JSON.parse(text);
    } catch {
        return null;
    }
}

function failMessage(res, text, parsed) {
    if (text && (text.includes("Proxy error") || text.includes("ECONNREFUSED"))) {
        return "Cannot reach API — start the backend on port 8000 (e.g. uvicorn backend.src.main:app --port 8000).";
    }
    if (parsed && parsed.detail != null) {
        const d = parsed.detail;
        if (typeof d === "string") return d;
        if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
    }
    if (text && text.length < 600) return text.replace(/\s+/g, " ").trim();
    return `Request failed (${res.status})`;
}

export async function fetchJson(url, init) {
    const res = await fetch(url, init);
    const text = await res.text();
    const parsed = tryParseJson(text);
    if (!res.ok) {
        throw new Error(failMessage(res, text, parsed));
    }
    if (parsed === null || parsed === undefined) return {};
    return parsed;
}
