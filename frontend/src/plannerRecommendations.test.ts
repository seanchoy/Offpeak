import { describe, expect, it } from "vitest";

import { findMentionedPois, formatPoiType } from "./plannerRecommendations";
import type { Poi } from "./types";

function poi(slug: string, name: string): Poi {
  return { slug, name, type: "park", borough: "Manhattan" } as Poi;
}

const CATALOGUE = [
  poi("central-park", "Central Park"),
  poi("the-pond-central-park", "The Pond Central Park"),
  poi("the-ramble-central-park", "The Ramble Central Park"),
  poi("greenacre-park", "Greenacre Park"),
  poi("edge", "Edge"),
];

const slugs = (pois: Poi[]) => pois.map((item) => item.slug);

describe("findMentionedPois", () => {
  it("returns the named attractions in the order the reply mentions them", () => {
    const reply =
      "The Pond Central Park is tranquil, Greenacre Park has a waterfall, " +
      "and The Ramble Central Park is a secluded woodland.";

    expect(slugs(findMentionedPois(reply, CATALOGUE))).toEqual([
      "the-pond-central-park",
      "greenacre-park",
      "the-ramble-central-park",
    ]);
  });

  it("matches whole words in any case and treats a hyphen as part of a word", () => {
    expect(slugs(findMentionedPois("a cutting-edge gallery, knowledge", CATALOGUE))).toEqual([]);
    expect(slugs(findMentionedPois("Head up the edge at sunset.", CATALOGUE))).toEqual(["edge"]);
  });

  it("still finds a short name that is mentioned on its own", () => {
    const reply = "The Ramble Central Park, and later Central Park's lawns.";

    expect(slugs(findMentionedPois(reply, CATALOGUE))).toEqual([
      "the-ramble-central-park",
      "central-park",
    ]);
  });

  it("keeps at most the given number of places", () => {
    const reply = "Edge, Greenacre Park and Central Park.";

    expect(slugs(findMentionedPois(reply, CATALOGUE, 2))).toEqual(["edge", "greenacre-park"]);
  });
});

describe("formatPoiType", () => {
  it("turns a type value into a label", () => {
    expect(formatPoiType("museum")).toBe("Museum");
    expect(formatPoiType("observation_deck")).toBe("Observation deck");
  });
});
