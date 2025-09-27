import React, { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim() === "") return;
    alert(`Analyzing: ${url}`); // replace with your backend call
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
      <h1 className="title">SEO Analyzer</h1>

      {/* Search Box */}
      <form className="search-box" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Enter a website URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button type="submit">Go</button>
      </form>

      {/* Examples */}
      <p className="subtitle">Or try these popular websites:</p>
      <div className="examples">
        {examples.map((site, i) => (
          <button
            key={i}
            onClick={() => setUrl(site)}
            className="example-btn"
          >
            {site}
          </button>
        ))}
      </div>

      <p className="footer">🔍 Analyze SEO of any site instantly</p>
    </div>
  );
}

export default App;
