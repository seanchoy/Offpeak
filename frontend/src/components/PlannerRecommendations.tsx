import poiPhotoFallback from "../assets/poi-photo-fallback.svg";
import { formatPoiType } from "../plannerRecommendations";
import type { Poi } from "../types";

type PlannerRecommendationsProps = {
  pois: Poi[];
};

/*
  Cards for the attractions a planner reply names. Each opens the attraction
  in a new tab, so the conversation (which lives only in this page's state)
  is still there when the visitor comes back.
*/
function PlannerRecommendations({ pois }: PlannerRecommendationsProps) {
  if (pois.length === 0) {
    return null;
  }

  return (
    <ul className="ai-recommendations" aria-label="Places in this reply">
      {pois.map((poi) => {
        const place = [formatPoiType(poi.type), poi.neighborhood || poi.borough]
          .filter(Boolean)
          .join(" · ");

        return (
          <li key={poi.slug}>
            <a
              className="ai-recommendation-card"
              href={`/explore/${encodeURIComponent(poi.slug)}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <img
                src={poi.hero_image_url || poiPhotoFallback}
                alt=""
                loading="lazy"
                onError={(event) => {
                  if (!event.currentTarget.src.endsWith("poi-photo-fallback.svg")) {
                    event.currentTarget.src = poiPhotoFallback;
                  }
                }}
              />
              <span className="ai-recommendation-body">
                {place && <span className="ai-recommendation-meta">{place}</span>}
                <strong>{poi.name}</strong>
                {poi.summary && (
                  <span className="ai-recommendation-summary">{poi.summary}</span>
                )}
                <span className="ai-recommendation-link">
                  View details
                  <span aria-hidden="true"> ↗</span>
                  <span className="sr-only"> (opens in a new tab)</span>
                </span>
              </span>
            </a>
          </li>
        );
      })}
    </ul>
  );
}

export default PlannerRecommendations;
