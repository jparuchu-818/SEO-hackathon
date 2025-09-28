import React, { useState, useEffect, useRef } from "react";
import "./App.css";

function ResultCard({ url }) {
  const [copyButtonText, setCopyButtonText] = useState("Copy Link");

  const handleCopyLink = () => {
    navigator.clipboard
      .writeText(url)
      .then(() => {
        setCopyButtonText("Copied!");
        setTimeout(() => setCopyButtonText("Copy Link"), 2000);
      })
      .catch(() => {
        setCopyButtonText("Failed!");
        setTimeout(() => setCopyButtonText("Copy Link"), 2000);
      });
  };

  return (
    <div className="result-card">
      <h2 className="result-title">✅ Presentation Ready!</h2>
      <p className="result-url">{url}</p>
      <div className="result-actions">
        <a href={url} target="_blank" rel="noopener noreferrer" className="action-btn open-btn">
          🚀 Open in New Tab
        </a>
        <button onClick={handleCopyLink} className="action-btn copy-btn">
          {copyButtonText}
        </button>
      </div>
    </div>
  );
}

function App() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("🔍 Analyze SEO of any site instantly");
  const [isLoading, setIsLoading] = useState(false);
  const [finalUrl, setFinalUrl] = useState("");

  const pollingIntervalRef = useRef();

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  const pollStatus = (jobId) => {
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/report-status/${jobId}`);
        if (!response.ok) throw new Error("Status check failed");

        const data = await response.json();
        switch (data.status) {
          case "fetching_data":
            setStatus("Step 1/3: 📡 Fetching SEO data...");
            break;
          case "generating_text":
            setStatus("Step 2/3: 🧠 Generating insights with AI...");
            break;
          case "creating_presentation":
            setStatus("Step 3/3: 🎨 Creating your presentation...");
            break;
          case "complete":
            clearInterval(pollingIntervalRef.current);
            setStatus("✅ Report complete!");
            setFinalUrl(data.result);
            setIsLoading(false);
            break;
          case "failed":
            clearInterval(pollingIntervalRef.current);
            setStatus(`❌ Report failed: ${data.result}`);
            setIsLoading(false);
            break;
          default:
            setStatus("⏳ Waiting in queue...");
        }
      } catch (error) {
        clearInterval(pollingIntervalRef.current);
        setStatus("⚠️ Error: Could not connect to backend.");
        setIsLoading(false);
      }
    }, 5000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (url.trim() === "" || isLoading) return;

    setIsLoading(true);
    setFinalUrl("");
    setStatus("⏳ Submitting job to server...");

    try {
      const response = await fetch("http://127.0.0.1:8000/generate-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) throw new Error("Job start failed.");

      const result = await response.json();
      setStatus("📡 Job submitted, polling for results...");
      pollStatus(result.job_id);
    } catch (error) {
      console.error("Submit error:", error);
      setStatus("⚠️ Could not connect to backend.");
      setIsLoading(false);
    }
  };

  const examples = [
    "https://www.nytimes.com",
    "https://www.bbc.com",
    "https://www.wikipedia.org",
    "https://www.apple.com",
    "https://www.microsoft.com",
    "https://www.tesla.com",
  ];

  return (
    <div className="app">
      {finalUrl ? (
        <ResultCard url={finalUrl} />
      ) : (
        <>
          <h1 className="title">SEO Analyzer</h1>

          {/* Input */}
          <form className="search-box" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Enter a website URL..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>
              {isLoading ? "Analyzing..." : "Go"}
            </button>
          </form>

          {/* Example URLs */}
          <p className="subtitle">Or try these popular websites:</p>
          <div className="examples">
            {examples.map((site, i) => (
              <button
                key={i}
                onClick={() => setUrl(site)}
                className="example-btn"
                disabled={isLoading}
              >
                {site}
              </button>
            ))}
          </div>

          <p className="footer">{status}</p>
        </>
      )}
    </div>
  );
}

export default App;