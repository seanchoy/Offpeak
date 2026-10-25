import type { BusynessResponse } from "../types";

type BusynessChartProps = {
  hours: BusynessResponse[];
  poiName: string;
};

type BusynessBand = "quiet" | "moderate" | "busy";

const BAND_LABELS: Record<BusynessBand, string> = {
  quiet: "Quiet",
  moderate: "Moderate",
  busy: "Busy",
};

// Upper edge of each band, also drawn as reference lines across the plot.
const QUIET_MAX = 35;
const MODERATE_MAX = 65;

function formatHour(hour: number): string {
  const normalisedHour = ((hour % 24) + 24) % 24;

  if (normalisedHour === 0) {
    return "12am";
  }

  if (normalisedHour === 12) {
    return "12pm";
  }

  return normalisedHour < 12
    ? `${normalisedHour}am`
    : `${normalisedHour - 12}pm`;
}

function getBusynessBand(busyness: number): BusynessBand {
  if (busyness <= QUIET_MAX) {
    return "quiet";
  }

  if (busyness <= MODERATE_MAX) {
    return "moderate";
  }

  return "busy";
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

/*
  A single-series column chart: height carries the crowd level, colour repeats
  it as a band, and only the quietest and busiest slots get a value label so
  the answer to "when should I go?" stands out. Every value is still available
  on hover/focus and in the screen-reader table.
*/
function BusynessChart({ hours, poiName }: BusynessChartProps) {
  const visibleHours = hours.slice(0, 24).map((hour) => ({
    ...hour,
    busyness: clampPercent(hour.busyness),
  }));

  if (visibleHours.length === 0) {
    return null;
  }

  const quietest = visibleHours.reduce((best, hour) =>
    hour.busyness < best.busyness ? hour : best
  );
  const busiest = visibleHours.reduce((worst, hour) =>
    hour.busyness > worst.busyness ? hour : worst
  );
  const isDense = visibleHours.length > 12;

  return (
    <figure className="busyness-forecast">
      <div className="busyness-chart-heading">
        <figcaption>
          <span className="busyness-chart-title">Crowd forecast</span>
          <span className="busyness-chart-summary">
            Quietest at <strong>{formatHour(quietest.hour_of_day)}</strong>
            {quietest.hour_of_day !== busiest.hour_of_day && (
              <>
                {" · "}busiest at{" "}
                <strong>{formatHour(busiest.hour_of_day)}</strong>
              </>
            )}
          </span>
        </figcaption>

        <ul className="busyness-chart-legend" aria-label="Crowd levels">
          {(Object.keys(BAND_LABELS) as BusynessBand[]).map((band) => (
            <li key={band}>
              <i className={band} aria-hidden="true" />
              {BAND_LABELS[band]}
            </li>
          ))}
        </ul>
      </div>

      <div className="mini-busyness-chart" aria-hidden="true">
        <div className="busyness-plot">
          {[MODERATE_MAX, QUIET_MAX].map((edge) => (
            <span
              key={edge}
              className="busyness-threshold"
              style={{ bottom: `${edge}%` }}
            >
              <small>{edge}%</small>
            </span>
          ))}

          {visibleHours.map((hour) => {
            const band = getBusynessBand(hour.busyness);
            const isHighlighted = hour === quietest || hour === busiest;

            return (
              <div
                key={hour.hour_of_day}
                className={`mini-busyness-column ${band}`}
              >
                {isHighlighted && !isDense && (
                  <span
                    className="busyness-value"
                    style={{ bottom: `${hour.busyness}%` }}
                  >
                    {hour.busyness}%
                  </span>
                )}

                <span
                  className="mini-busyness-bar"
                  style={{ height: `max(3px, ${hour.busyness}%)` }}
                >
                  {/* Anchored to the bar so it opens just above the cap. */}
                  <span className="busyness-tooltip">
                    <strong>{hour.busyness}%</strong>
                    {formatHour(hour.hour_of_day)} · {BAND_LABELS[band]}
                  </span>
                </span>
              </div>
            );
          })}
        </div>

        <div className="busyness-axis">
          {visibleHours.map((hour, index) => {
            const showLabel =
              !isDense || index % 3 === 0 || index === visibleHours.length - 1;

            return (
              <span key={hour.hour_of_day}>
                {showLabel ? formatHour(hour.hour_of_day) : ""}
              </span>
            );
          })}
        </div>
      </div>

      <table className="sr-only">
        <caption>Crowd forecast for {poiName}</caption>
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">Expected crowd</th>
          </tr>
        </thead>
        <tbody>
          {visibleHours.map((hour) => (
            <tr key={hour.hour_of_day}>
              <th scope="row">{formatHour(hour.hour_of_day)}</th>
              <td>
                {hour.busyness}% ({BAND_LABELS[getBusynessBand(hour.busyness)]})
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

export default BusynessChart;
