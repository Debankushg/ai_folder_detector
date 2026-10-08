"use client";
import { useState } from "react";
import Diagram from "../components/Diagram";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Node = { id: string; label: string; type: string; description: string; files: string[] };
type Tech = { name: string; category: string; detail: string };
type Result = {
  tech: { frontend: Tech[]; backend: Tech[]; other: Tech[] };
  name: string; mode: string; warning: string | null; summary: string; nodes: Node[]; mermaid: string;
  stats: { files: number; languages: Record<string, number>; entry_points: string[] };
};

export default function Home() {
  const [tab, setTab] = useState<"github" | "upload">("github");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  async function analyze() {
    setLoading(true); setError(""); setResult(null);
    try {
      let res: Response;
      if (tab === "github") {
        res = await fetch(`${API}/api/analyze/github`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }),
        });
      } else {
        if (!file) throw new Error("Choose a .zip of your project folder first.");
        const form = new FormData();
        form.append("file", file);
        res = await fetch(`${API}/api/analyze/upload`, { method: "POST", body: form });
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? `Request failed (${res.status})`);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>FlowMap</h1>
      <p className="muted">Upload a project (zip) or paste a GitHub link to see its flow as a block diagram.</p>

      <div className="card">
        <div className="tabs">
          <button className={`tab ${tab === "github" ? "active" : ""}`} onClick={() => setTab("github")}>GitHub link</button>
          <button className={`tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>Upload folder (.zip)</button>
        </div>
        <div className="row">
          {tab === "github" ? (
            <input type="text" placeholder="https://github.com/owner/repo" value={url} onChange={(e) => setUrl(e.target.value)} />
          ) : (
            <input type="file" accept=".zip" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          )}
          <button className="go" disabled={loading || (tab === "github" && !url)} onClick={analyze}>
            {loading ? "Analyzing…" : "Generate diagram"}
          </button>
        </div>
        {error && <div className="err">{error}</div>}
      </div>

      {result && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>{result.name}</h2>
          <p>{result.summary}</p>
          {result.warning && <div className="warn">{result.warning}</div>}
          <div className="chips">
            <span className="chip">{result.stats.files} files</span>
            <span className="chip">mode: {result.mode}</span>
            {Object.entries(result.stats.languages).slice(0, 5).map(([l, n]) => (
              <span className="chip" key={l}>{l}: {n}</span>
            ))}
          </div>
          <h3>Technologies used</h3>
          <div className="tech-grid">
            <TechColumn title="Frontend" items={result.tech.frontend} />
            <TechColumn title="Backend" items={result.tech.backend} />
            {result.tech.other.length > 0 && <TechColumn title="Database / DevOps / Other" items={result.tech.other} />}
          </div>
          <h3>Flow diagram</h3>
          <Diagram code={result.mermaid} />
          <h3>Blocks</h3>
          <div className="nodes">
            {result.nodes.map((n) => (
              <div className="node" key={n.id}>
                <h4>{n.label} <span className="chip">{n.type}</span></h4>
                <div>{n.description}</div>
                {n.files.length > 0 && <small>{n.files.join(", ")}</small>}
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}

function TechColumn({ title, items }: { title: string; items: Tech[] }) {
  return (
    <div className="node">
      <h4>{title}</h4>
      {items.length === 0 && <small>None detected</small>}
      {items.map((t) => (
        <div className="tech-item" key={t.name} title={t.detail}>
          <strong>{t.name}</strong> {t.category && <span className="chip">{t.category}</span>}
          {t.detail && <small>{t.detail}</small>}
        </div>
      ))}
    </div>
  );
}
