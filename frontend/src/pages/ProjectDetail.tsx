import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import client from "../api/client";

interface ImageAsset {
  id: number;
  original_filename: string;
  uploaded_at: string;
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [images, setImages] = useState<ImageAsset[]>([]);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    client.get<ImageAsset[]>(`/projects/${id}/images`).then((response) => setImages(response.data));
  }, [id]);

  async function handleUpload() {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const response = await client.post<ImageAsset>(`/projects/${id}/images`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setImages((prev) => [...prev, response.data]);
    setFile(null);
  }

  return (
    <div>
      <h1>Project Images</h1>
      <input
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={handleUpload} disabled={!file}>
        Upload
      </button>
      <ul>
        {images.map((image) => (
          <li key={image.id}>{image.original_filename}</li>
        ))}
      </ul>
    </div>
  );
}
