import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import client from "../api/client";
import { Layout } from "../components/Layout";

interface RecentActivityItem {
  id: number;
  generation_type: string;
  status: string;
  created_at: string;
}

interface ProjectAnalytics {
  total_images: number;
  total_generations: number;
  generations_by_status: Record<string, number>;
  average_quality_score: number | null;
  storage_usage_bytes: number;
  recent_activity: RecentActivityItem[];
}

export function Analytics() {
  const { id } = useParams<{ id: string }>();
  const [analytics, setAnalytics] = useState<ProjectAnalytics | null>(null);

  useEffect(() => {
    client.get<ProjectAnalytics>(`/projects/${id}/analytics`).then((response) => setAnalytics(response.data));
  }, [id]);

  return (
    <Layout>
      <div className="spread page-header">
        <div>
          <h1>Project Analytics</h1>
          <p>Generation history, quality trends, and storage usage for this project.</p>
        </div>
        <Link to={`/projects/${id}`}>&larr; Back to project</Link>
      </div>

      {!analytics ? (
        <p className="muted">Loading...</p>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-tile-label">Total images</div>
              <div className="stat-tile-value">{analytics.total_images}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Total generations</div>
              <div className="stat-tile-value">{analytics.total_generations}</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Storage used</div>
              <div className="stat-tile-value">{(analytics.storage_usage_bytes / 1024).toFixed(1)} KB</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-label">Avg. quality score</div>
              <div className="stat-tile-value">{analytics.average_quality_score ?? "N/A"}</div>
            </div>
          </div>

          <h2>Generations by status</h2>
          {Object.keys(analytics.generations_by_status).length === 0 ? (
            <div className="empty-state">No generations yet.</div>
          ) : (
            <div className="row">
              {Object.entries(analytics.generations_by_status).map(([status, count]) => (
                <span key={status} className={`badge badge-${status}`}>
                  {status}: {count}
                </span>
              ))}
            </div>
          )}

          <h2>Recent activity</h2>
          {analytics.recent_activity.length === 0 ? (
            <div className="empty-state">Nothing here yet.</div>
          ) : (
            <ul className="item-list">
              {analytics.recent_activity.map((item) => (
                <li key={item.id} className="item-row">
                  <span>
                    #{item.id} &middot; {item.generation_type}
                  </span>
                  <span className="muted">{new Date(item.created_at).toLocaleString()}</span>
                  <span className={`badge badge-${item.status}`}>{item.status}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Layout>
  );
}
