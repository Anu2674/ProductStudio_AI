import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import client from "../api/client";
import { Layout } from "../components/Layout";
import { Thumbnail } from "../components/Thumbnail";

interface ImageAsset {
  id: number;
  original_filename: string;
  uploaded_at: string;
}

interface Generation {
  id: number;
  generation_type: string;
  status: string;
  prompt: string | null;
  quality_score: { overall: number } | null;
  result_storage_path: string | null;
}

interface MarketingContent {
  title: string;
  description: string;
  bullet_points: string[];
  social_caption: string;
  seo_keywords: string[];
}

async function downloadBlob(url: string, filename: string) {
  const response = await client.get(url, { responseType: "blob" });
  const objectUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [images, setImages] = useState<ImageAsset[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [search, setSearch] = useState("");
  const [marketingByImage, setMarketingByImage] = useState<Record<number, MarketingContent>>({});
  const [loadingImages, setLoadingImages] = useState(true);
  const [uploading, setUploading] = useState(false);

  function refreshImages() {
    return client.get<ImageAsset[]>(`/projects/${id}/images`).then((response) => {
      setImages(response.data);
      setLoadingImages(false);
    });
  }

  function refreshGenerations() {
    return client
      .get<Generation[]>(`/projects/${id}/generations`, { params: search ? { search } : {} })
      .then((response) => setGenerations(response.data));
  }

  useEffect(() => {
    refreshImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    refreshGenerations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, search]);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await client.post<ImageAsset>(`/projects/${id}/images`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImages((prev) => [...prev, response.data]);
      setFile(null);
    } finally {
      setUploading(false);
    }
  }

  async function handleSegment(imageId: number) {
    await client.post(`/projects/${id}/images/${imageId}/segment`);
    setTimeout(refreshGenerations, 1500);
  }

  async function handleGenerate(imageId: number) {
    await client.post(`/projects/${id}/images/${imageId}/generate`, {
      scene_type: "studio_white",
      lighting: "soft",
      camera_angle: "front",
    });
    setTimeout(refreshGenerations, 1500);
  }

  async function handleGenerateMarketing(imageId: number, filename: string) {
    const productName = filename.replace(/\.[^.]+$/, "");
    const response = await client.post<MarketingContent>(
      `/projects/${id}/images/${imageId}/marketing-content`,
      { product_name: productName }
    );
    setMarketingByImage((prev) => ({ ...prev, [imageId]: response.data }));
  }

  return (
    <Layout>
      <div className="spread page-header">
        <div>
          <h1>Project Images</h1>
          <p>Upload a photo, then remove its background, generate a styled scene, or write marketing copy.</p>
        </div>
        <Link to={`/projects/${id}/analytics`}>View analytics &rarr;</Link>
      </div>

      <div className="upload-zone">
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </div>

      {loadingImages ? (
        <p className="muted">Loading images...</p>
      ) : images.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#128444;&#65039;</div>
          <strong>No images yet</strong>
          <span>Upload a product photo above to get started.</span>
        </div>
      ) : (
        <div className="image-grid">
          {images.map((image) => (
            <div key={image.id} className="image-card">
              <Thumbnail url={`/images/${image.id}/file`} alt={image.original_filename} />
              <div className="image-card-body">
                <span className="image-card-filename" title={image.original_filename}>
                  {image.original_filename}
                </span>
                <div className="image-card-actions">
                  <button className="secondary sm" onClick={() => handleSegment(image.id)}>
                    Remove background
                  </button>
                  <button className="secondary sm" onClick={() => handleGenerate(image.id)}>
                    Generate photo
                  </button>
                  <button
                    className="secondary sm"
                    onClick={() => handleGenerateMarketing(image.id, image.original_filename)}
                  >
                    Marketing copy
                  </button>
                </div>
                {marketingByImage[image.id] && (
                  <div className="marketing-panel">
                    <strong>{marketingByImage[image.id].title}</strong>
                    <p style={{ margin: "6px 0" }}>{marketingByImage[image.id].description}</p>
                    <ul>
                      {marketingByImage[image.id].bullet_points.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                    <p className="muted">{marketingByImage[image.id].social_caption}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="spread" style={{ marginTop: 40 }}>
        <h2 style={{ marginTop: 0 }}>Generations</h2>
        <input
          className="input-narrow"
          placeholder="Search by prompt"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {generations.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">&#10024;</div>
          <strong>No generations yet</strong>
          <span>Try &quot;Generate photo&quot; on an image above.</span>
        </div>
      ) : (
        <ul className="item-list">
          {generations.map((generation) => (
            <li key={generation.id} className="generation-card">
              {generation.result_storage_path ? (
                <Thumbnail
                  url={`/generations/${generation.id}/file`}
                  alt={`Generation ${generation.id}`}
                  className="generation-thumb"
                />
              ) : (
                <div className="generation-thumb" />
              )}
              <div className="item-row-main" style={{ flex: 1 }}>
                <span>
                  #{generation.id} &middot; {generation.generation_type}
                  {generation.quality_score && ` · quality ${generation.quality_score.overall}`}
                </span>
                <span className={`badge badge-${generation.status}`} style={{ width: "fit-content" }}>
                  {generation.status}
                </span>
              </div>
              {generation.result_storage_path && (
                <div className="item-actions">
                  <button
                    className="secondary sm"
                    onClick={() =>
                      downloadBlob(`/generations/${generation.id}/file`, `generation_${generation.id}.png`)
                    }
                  >
                    Download
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Layout>
  );
}
