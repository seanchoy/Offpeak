import { apiFetch } from "./api";

/*
  Who took a POI's Google Places photo. Google's terms require crediting the
  author wherever the full-size photo is shown, and letting people open the
  original on Google Maps.
*/
export type PhotoAttribution = {
  author_name: string | null;
  author_uri: string | null;
  google_maps_uri: string | null;
};

/* True when a hero image is served by our Google Places photo proxy. */
export function isGooglePlacesPhoto(
  heroImageUrl: string | null | undefined,
  slug: string
): boolean {
  return Boolean(heroImageUrl?.endsWith(`/api/pois/${slug}/photo`));
}

/*
  The credit is supplementary, so any failure (no photo, backend not updated,
  network) resolves to null and the page simply shows the photo without it.
*/
export async function fetchPhotoAttribution(
  slug: string
): Promise<PhotoAttribution | null> {
  try {
    return await apiFetch<PhotoAttribution>(
      `/api/pois/${encodeURIComponent(slug)}/photo/attribution`
    );
  } catch (error) {
    console.info("Photo attribution was not loaded:", error);
    return null;
  }
}
