import { useEffect, useState } from "react";

import client from "../api/client";

interface ThumbnailProps {
  url: string;
  alt: string;
  className?: string;
}

export function Thumbnail({ url, alt, className = "image-thumb" }: ThumbnailProps) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    client
      .get(url, { responseType: "blob" })
      .then((response) => {
        if (cancelled) return;
        objectUrl = window.URL.createObjectURL(new Blob([response.data]));
        setSrc(objectUrl);
      })
      .catch(() => setSrc(null));

    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [url]);

  if (!src) {
    return <div className={`${className} image-thumb-placeholder`} aria-label={alt} />;
  }
  return <img className={className} src={src} alt={alt} />;
}
