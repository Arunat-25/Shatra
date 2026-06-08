import React from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatBucketLabel, getAdminChartColors, getAdminChartTooltipStyle } from './adminChartTheme';

export default function AdminMultiLineChart({ buckets, granularity, emptyLabel }) {
  const { t } = useTranslation();
  const colors = getAdminChartColors();
  const data = (buckets || []).map((b) => ({
    ...b,
    label: formatBucketLabel(b.ts, granularity),
  }));

  if (!data.length || data.every((d) => d.total_unique === 0)) {
    return <p className="admin-chart-empty">{emptyLabel}</p>;
  }

  return (
    <div className="admin-chart" role="img">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fill: colors.muted, fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis allowDecimals={false} tick={{ fill: colors.muted, fontSize: 11 }} width={36} />
          <Tooltip
            contentStyle={getAdminChartTooltipStyle(colors)}
            labelStyle={{ color: colors.text }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="total_unique"
            name={t('admin.charts.legendTotal')}
            stroke={colors.accent}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="registered_unique"
            name={t('admin.charts.legendRegistered')}
            stroke={colors.line2}
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="anonymous_unique"
            name={t('admin.charts.legendAnonymous')}
            stroke={colors.line3}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

AdminMultiLineChart.propTypes = {
  buckets: PropTypes.arrayOf(
    PropTypes.shape({
      ts: PropTypes.string.isRequired,
      total_unique: PropTypes.number.isRequired,
      registered_unique: PropTypes.number.isRequired,
      anonymous_unique: PropTypes.number.isRequired,
    }),
  ),
  granularity: PropTypes.oneOf(['hour', 'day']).isRequired,
  emptyLabel: PropTypes.string.isRequired,
};
