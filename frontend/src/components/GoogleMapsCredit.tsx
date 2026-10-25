/*
  Places data (ratings, photos) shown outside a Google map must carry a Google
  Maps attribution near the content it covers.
*/
function GoogleMapsCredit() {
  return (
    <p className="google-maps-credit">
      Photos and ratings: <span translate="no">Google Maps</span>
    </p>
  );
}

export default GoogleMapsCredit;
