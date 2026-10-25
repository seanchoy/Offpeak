import type { PhotoAttribution } from "../poiPhoto";

type PhotoCreditProps = {
  attribution: PhotoAttribution;
};

/*
  "Photo by <author> on Google Maps": credits the photographer and links to
  the original photo, as the Google Maps Platform terms require. The words
  "Google Maps" are kept exactly as Google specifies (no translation or
  restyling of the name).
*/
function PhotoCredit({ attribution }: PhotoCreditProps) {
  const authorName = attribution.author_name || "a Google Maps contributor";

  return (
    <figcaption className="photo-credit">
      Photo by{" "}
      {attribution.author_uri ? (
        <a href={attribution.author_uri} target="_blank" rel="noopener noreferrer">
          {authorName}
        </a>
      ) : (
        authorName
      )}{" "}
      on{" "}
      {attribution.google_maps_uri ? (
        <a
          href={attribution.google_maps_uri}
          target="_blank"
          rel="noopener noreferrer"
        >
          Google Maps
        </a>
      ) : (
        "Google Maps"
      )}
    </figcaption>
  );
}

export default PhotoCredit;
