interface BarData {
  label: string;
  value: number;
  total?: number;
}

interface StatsChartsProps {
  data: BarData[];
  title: string;
}

function accuracyColor(pct: number): string {
  if (pct >= 70) return "var(--color-success)";
  if (pct >= 50) return "var(--color-warning)";
  return "var(--color-error)";
}

export default function StatsCharts({ data, title }: StatsChartsProps) {
  if (data.length === 0) return null;

  return (
    <div className="stats-chart">
      <h3 className="stats-chart-title">{title}</h3>
      <div className="stats-chart-bars">
        {data.map((d) => {
          const pct =
            d.total != null && d.total > 0
              ? Math.round((d.value / d.total) * 100)
              : Math.round(d.value);
          const barWidth = Math.max(pct, 2);

          return (
            <div className="bar-row" key={d.label}>
              <span className="bar-label">{d.label}</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: `${barWidth}%`,
                    background: accuracyColor(pct),
                  }}
                />
              </div>
              <span
                className="bar-pct"
                style={{ color: accuracyColor(pct) }}
              >
                {pct}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
