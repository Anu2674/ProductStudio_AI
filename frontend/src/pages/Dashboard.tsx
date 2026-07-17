import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import client from "../api/client";
import { Layout } from "../components/Layout";

interface Project {
  id: number;
  name: string;
  description: string | null;
}

const AVATAR_COLORS = ["#4f46e5", "#0891b2", "#c2410c", "#15803d", "#a21caf", "#b91c1c"];

function avatarColor(seed: number) {
  return AVATAR_COLORS[seed % AVATAR_COLORS.length];
}

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get<Project[]>("/projects").then((response) => {
      setProjects(response.data);
      setLoading(false);
    });
  }, []);

  async function handleCreate() {
    if (!name.trim()) return;
    const response = await client.post<Project>("/projects", { name: name.trim() });
    setProjects((prev) => [...prev, response.data]);
    setName("");
  }

  return (
    <Layout>
      <div className="page-header">
        <h1>Your Projects</h1>
        <p>Organize product photos into projects, then generate, enhance, and score images inside each one.</p>
      </div>

      <div className="upload-zone">
        <input
          className="input-narrow"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button onClick={handleCreate} disabled={!name.trim()}>
          Create Project
        </button>
      </div>

      {loading ? (
        <p className="muted">Loading projects...</p>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#128247;</div>
          <strong>No projects yet</strong>
          <span>Create your first project above to start uploading product photos.</span>
        </div>
      ) : (
        <div className="project-grid">
          {projects.map((project) => (
            <div key={project.id} className="project-card">
              <div className="project-card-avatar" style={{ background: avatarColor(project.id) }}>
                {project.name.charAt(0).toUpperCase()}
              </div>
              <Link to={`/projects/${project.id}`} className="project-card-title">
                {project.name}
              </Link>
              {project.description && <span className="muted">{project.description}</span>}
              <div className="project-card-footer">
                <span className="muted">Project #{project.id}</span>
                <Link to={`/projects/${project.id}/analytics`}>Analytics</Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
