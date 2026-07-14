import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import client from "../api/client";

interface Project {
  id: number;
  name: string;
  description: string | null;
}

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");

  useEffect(() => {
    client.get<Project[]>("/projects").then((response) => setProjects(response.data));
  }, []);

  async function handleCreate() {
    const response = await client.post<Project>("/projects", { name });
    setProjects((prev) => [...prev, response.data]);
    setName("");
  }

  return (
    <div>
      <h1>Your Projects</h1>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New project name" />
      <button onClick={handleCreate}>Create Project</button>
      <ul>
        {projects.map((project) => (
          <li key={project.id}>
            <Link to={`/projects/${project.id}`}>{project.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
