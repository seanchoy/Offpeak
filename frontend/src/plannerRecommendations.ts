import type { Poi } from "./types";

export const MAX_PLANNER_RECOMMENDATIONS = 6;

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/*
  The catalogue attractions an AI Planner reply names, in the order the reply
  mentions them. It follows the backend grounding check: whole words in any
  case, where a hyphen counts as part of a word ("cutting-edge" is not Edge),
  and the longest names are matched first so "The Ramble Central Park" is not
  also counted as "Central Park". A matched name is blanked out with spaces of
  the same length, which keeps the positions of the other names unchanged.
*/
export function findMentionedPois(
  text: string,
  pois: Poi[],
  limit = MAX_PLANNER_RECOMMENDATIONS
): Poi[] {
  let remaining = text;
  const found = new Map<string, { poi: Poi; position: number }>();
  const longestFirst = [...pois].sort((a, b) => b.name.length - a.name.length);

  for (const poi of longestFirst) {
    const name = poi.name.trim();

    if (!name || found.has(poi.slug)) {
      continue;
    }

    const source = `(^|[^\\w-])${escapeRegExp(name)}(?![\\w-])`;
    const match = new RegExp(source, "i").exec(remaining);

    if (!match) {
      continue;
    }

    found.set(poi.slug, { poi, position: match.index + match[1].length });
    remaining = remaining.replace(
      new RegExp(source, "gi"),
      (_match, before: string) => before + " ".repeat(name.length)
    );
  }

  return [...found.values()]
    .sort((a, b) => a.position - b.position)
    .slice(0, limit)
    .map(({ poi }) => poi);
}

/* "museum" -> "Museum", "observation_deck" -> "Observation deck". */
export function formatPoiType(type: string): string {
  const words = type.replace(/[_-]+/g, " ").trim();
  return words ? words[0].toUpperCase() + words.slice(1) : "";
}
