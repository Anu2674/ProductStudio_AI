import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import client from "../api/client";

export function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await client.post("/auth/register", { email, password });
      navigate("/login");
    } catch {
      setError("Could not register. Email may already be in use.");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Create account</h1>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">Register</button>
    </form>
  );
}
