import React from 'react';
import PropTypes from 'prop-types';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatBucketLabel, getAdminChartColors } from './adminChartTheme';

export default function AdminLineChart({ buckets, granularity, emptyLabel }) {
  const colors = getAdminChartColors();
  const data = (buckets || []).map((b) => ({
    ...b,
    label: formatBucketLabel(b.ts, granularity),
  }));

  if (!data.length || data.every((d) => d.count === 0)) {
    return <p className="admin-chart-empty">{emptyLabel}</p>;
  }

  return (
    <div className="admin-chart" role="img" aria-hidden={false}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fill: colors.muted, fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: colors.muted, fontSize: 11 }}
            width={36}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--surface, #1a1a1a)',
              border: '1px solid var(--border, rgba(255,255,255,0.12))',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: colors.text }}
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke={colors.accent}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

AdminLineChart.propTypes = {
  buckets: PropTypes.arrayOf(
    PropTypes.shape({
      ts: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    }),
  ),
  granularity: PropTypes.oneOf(['hour', 'day']).isRequired,
  emptyLabel: PropTypes.string.isRequired,
};
