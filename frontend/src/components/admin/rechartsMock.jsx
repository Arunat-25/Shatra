/** Minimal recharts stub for component tests. */

export function ResponsiveContainer({ children }) {
  return <div data-testid="recharts-container">{children}</div>;
}

export function LineChart({ children, data }) {
  return (
    <div data-testid="line-chart" data-points={data?.length ?? 0}>
      {children}
    </div>
  );
}

export function PieChart({ children }) {
  return <div data-testid="pie-chart">{children}</div>;
}

export function CartesianGrid() {
  return null;
}

export function XAxis() {
  return null;
}

export function YAxis() {
  return null;
}

export function Tooltip() {
  return null;
}

export function Legend() {
  return null;
}

export function Line({ dataKey }) {
  return <div data-testid={`line-${dataKey}`} />;
}

export function Pie({ data }) {
  return <div data-testid="pie" data-slices={data?.length ?? 0} />;
}

export function Cell() {
  return null;
}
