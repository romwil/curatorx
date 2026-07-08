import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

export default function TitleDetailPage() {
  const { mediaType, itemId } = useParams();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/title/${mediaType}/${itemId}`)
      .then(setDetail)
      .catch((err) => setError(err.message));
  }, [mediaType, itemId]);

  if (error) return <p className="error">{error}</p>;
  if (!detail) return <p>Loading…</p>;

  return (
    <div className="title-page">
      <Link to="/">← Back to chat</Link>
      <div className="title-hero" style={{ backgroundImage: detail.backdrop_url ? `url(${detail.backdrop_url})` : undefined }}>
        <div className="title-hero-content">
          {detail.poster_url ? <img src={detail.poster_url} alt="" className="hero-poster" /> : null}
          <div>
            <p className="eyebrow">{detail.media_type === "movie" ? "Movie" : "TV Show"}</p>
            <h1>
              {detail.title}
              {detail.year ? ` (${detail.year})` : ""}
            </h1>
            {detail.rating ? <p>TMDB {detail.rating.toFixed(1)}</p> : null}
            {detail.in_library ? <span className="badge">In your library</span> : null}
            <p>{detail.overview}</p>
            {detail.genres?.length ? <p>{detail.genres.join(" · ")}</p> : null}
            {detail.purge_reason ? <p className="purge-note">Purge consideration: {detail.purge_reason}</p> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
