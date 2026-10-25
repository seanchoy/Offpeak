import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PhotoCredit from "./PhotoCredit";

describe("PhotoCredit", () => {
  it("credits the author and links to the original on Google Maps", () => {
    render(
      <PhotoCredit
        attribution={{
          author_name: "Jane Doe",
          author_uri: "https://maps.google.com/contrib/1",
          google_maps_uri: "https://maps.google.com/photo/1",
        }}
      />
    );

    expect(screen.getByRole("link", { name: "Jane Doe" })).toHaveAttribute(
      "href",
      "https://maps.google.com/contrib/1"
    );
    expect(screen.getByRole("link", { name: "Google Maps" })).toHaveAttribute(
      "href",
      "https://maps.google.com/photo/1"
    );
  });

  it("still credits Google Maps when the author is unknown", () => {
    render(
      <PhotoCredit
        attribution={{ author_name: null, author_uri: null, google_maps_uri: null }}
      />
    );

    expect(screen.getByText(/google maps contributor/i)).toBeInTheDocument();
    expect(screen.getByText(/google maps$/i)).toBeInTheDocument();
  });
});
