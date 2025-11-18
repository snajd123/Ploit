import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

interface PositionalVPIPChartProps {
  vpip_utg?: number | null;
  vpip_hj?: number | null;
  vpip_mp?: number | null;
  vpip_co?: number | null;
  vpip_btn?: number | null;
  vpip_sb?: number | null;
  vpip_bb?: number | null;
}

const PositionalVPIPChart: React.FC<PositionalVPIPChartProps> = (props) => {
  // Optimal VPIP ranges by position
  const optimalRanges = {
    UTG: 15.5,
    HJ: 19.5,
    MP: 19.5,
    CO: 27.5,
    BTN: 47,
    SB: 33,
    BB: 38.5
  };

  const data = [
    { position: 'UTG', vpip: props.vpip_utg ?? 0, optimal: optimalRanges.UTG, hasData: props.vpip_utg !== null && props.vpip_utg !== undefined },
    { position: 'HJ', vpip: props.vpip_hj ?? 0, optimal: optimalRanges.HJ, hasData: props.vpip_hj !== null && props.vpip_hj !== undefined },
    { position: 'MP', vpip: props.vpip_mp ?? 0, optimal: optimalRanges.MP, hasData: props.vpip_mp !== null && props.vpip_mp !== undefined },
    { position: 'CO', vpip: props.vpip_co ?? 0, optimal: optimalRanges.CO, hasData: props.vpip_co !== null && props.vpip_co !== undefined },
    { position: 'BTN', vpip: props.vpip_btn ?? 0, optimal: optimalRanges.BTN, hasData: props.vpip_btn !== null && props.vpip_btn !== undefined },
    { position: 'SB', vpip: props.vpip_sb ?? 0, optimal: optimalRanges.SB, hasData: props.vpip_sb !== null && props.vpip_sb !== undefined },
    { position: 'BB', vpip: props.vpip_bb ?? 0, optimal: optimalRanges.BB, hasData: props.vpip_bb !== null && props.vpip_bb !== undefined },
  ];

  const getBarColor = (entry: typeof data[0]) => {
    if (!entry.hasData) return '#d1d5db'; // gray for no data
    const deviation = Math.abs(entry.vpip - entry.optimal);
    if (deviation < 5) return '#10b981'; // green - good
    if (deviation < 10) return '#f59e0b'; // yellow - ok
    return '#ef4444'; // red - bad
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Positional VPIP Analysis</h3>
      <p className="text-sm text-gray-600 mb-4">
        How tight/loose player is by position. Colors show deviation from optimal ranges.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="position" />
          <YAxis label={{ value: 'VPIP %', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            formatter={(value: number, name: string, props: any) => {
              if (name === 'vpip') {
                return [`${value.toFixed(1)}%`, 'Actual VPIP'];
              }
              if (name === 'optimal') {
                return [`${value.toFixed(1)}%`, 'Optimal Range'];
              }
              return value;
            }}
          />
          <ReferenceLine y={0} stroke="#000" />
          <Bar dataKey="optimal" fill="#94a3b8" fillOpacity={0.3} name="Optimal" />
          <Bar dataKey="vpip" name="Actual">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 flex items-center justify-center space-x-6 text-xs">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded"></div>
          <span className="text-gray-600">Good (&lt;5% deviation)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-yellow-500 rounded"></div>
          <span className="text-gray-600">OK (5-10% deviation)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span className="text-gray-600">Poor (&gt;10% deviation)</span>
        </div>
      </div>
    </div>
  );
};

export default PositionalVPIPChart;
