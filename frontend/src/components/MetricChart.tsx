import React from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';

interface MetricData {
  metric: string;
  value: number;
  fullMark: number;
}

interface MetricChartProps {
  data: MetricData[];
  title?: string;
}

const MetricChart: React.FC<MetricChartProps> = ({ data, title }) => {
  return (
    <div className="card">
      {title && <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="metric" />
          <PolarRadiusAxis angle={90} domain={[0, 100]} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.6}
          />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricChart;
