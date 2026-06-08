import React from 'react';
import PropTypes from 'prop-types';
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { getAdminChartColors, getAdminChartTooltipStyle } from './adminChartTheme';

const PIE_COLORS = ['#c9a227', '#6b9bd1', '#c97b6b', '#7bc96f', '#a78bfa'];

export default function AdminPieChart({ data, emptyLabel }) {
  const colors = getAdminChartColors();
  const items = (data || []).filter((d) => d.value > 0);

  if (!items.length) {
    return <p className="admin-chart-empty">{emptyLabel}</p>;
  }

  return (
    <div className="admin-chart admin-chart--pie" role="img">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={items}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="45%"
            outerRadius="75%"
            paddingAngle={2}
          >
            {items.map((entry, index) => (
              <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={getAdminChartTooltipStyle(colors)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

AdminPieChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    }),
  ),
  emptyLabel: PropTypes.string.isRequired,
};
