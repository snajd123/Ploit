import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Tooltip as CustomTooltip } from './Tooltip';

interface CBetStreetsChartProps {
  cbet_flop_pct?: number | null;
  cbet_turn_pct?: number | null;
  cbet_river_pct?: number | null;
}

const CBetStreetsChart: React.FC<CBetStreetsChartProps> = ({
  cbet_flop_pct,
  cbet_turn_pct,
  cbet_river_pct
}) => {
  const data = [
    {
      street: 'Flop',
      cbet: cbet_flop_pct ?? 0,
      optimal: 65,
      hasData: cbet_flop_pct !== null && cbet_flop_pct !== undefined
    },
    {
      street: 'Turn',
      cbet: cbet_turn_pct ?? 0,
      optimal: 50,
      hasData: cbet_turn_pct !== null && cbet_turn_pct !== undefined
    },
    {
      street: 'River',
      cbet: cbet_river_pct ?? 0,
      optimal: 40,
      hasData: cbet_river_pct !== null && cbet_river_pct !== undefined
    }
  ];

  // Calculate consistency (how much cbetting decreases across streets)
  const flopToTurn = (cbet_flop_pct ?? 0) - (cbet_turn_pct ?? 0);
  const turnToRiver = (cbet_turn_pct ?? 0) - (cbet_river_pct ?? 0);
  const avgDecline = (flopToTurn + turnToRiver) / 2;

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-lg font-semibold text-gray-900">Continuation Bet Frequency</h3>
        <CustomTooltip
          content={
            <div className="space-y-2 max-w-xs">
              <div className="font-semibold text-blue-300">C-Bet Consistency</div>
              <div className="text-xs text-gray-300">
                A continuation bet (c-bet) is when the preflop aggressor bets again on the flop. This chart
                shows how often they continue betting across streets (flop, turn, river).
              </div>
              <div className="text-xs border-t border-gray-700 pt-2">
                <div className="text-gray-400">Optimal Frequencies:</div>
                <ul className="text-gray-200 mt-1 space-y-1">
                  <li>• Flop: ~65% (high frequency)</li>
                  <li>• Turn: ~50% (moderate)</li>
                  <li>• River: ~40% (selective)</li>
                </ul>
              </div>
              <div className="text-xs border-t border-gray-700 pt-2 text-gray-300">
                Large decline = gives up easily (exploitable with floats)
              </div>
            </div>
          }
          position="top"
          iconSize={16}
        />
      </div>
      <p className="text-sm text-gray-600 mb-4">
        Aggression consistency across streets. Decline per street: <span className="font-semibold text-blue-600">{avgDecline.toFixed(1)}%</span>
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="street" />
          <YAxis label={{ value: 'C-Bet %', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'cbet') return [`${value.toFixed(1)}%`, 'Actual C-Bet'];
              if (name === 'optimal') return [`${value.toFixed(1)}%`, 'Optimal'];
              return value;
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="optimal"
            stroke="#94a3b8"
            strokeDasharray="5 5"
            name="Optimal"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="cbet"
            stroke="#3b82f6"
            strokeWidth={3}
            name="Player C-Bet"
            dot={{ fill: '#3b82f6', r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-gray-600">Flop C-Bet</p>
          <p className="text-2xl font-bold text-blue-600">{(cbet_flop_pct ?? 0).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 mt-1">Optimal: ~65%</p>
        </div>
        <div className="p-3 bg-indigo-50 rounded-lg">
          <p className="text-gray-600">Turn C-Bet</p>
          <p className="text-2xl font-bold text-indigo-600">{(cbet_turn_pct ?? 0).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 mt-1">Optimal: ~50%</p>
        </div>
        <div className="p-3 bg-purple-50 rounded-lg">
          <p className="text-gray-600">River C-Bet</p>
          <p className="text-2xl font-bold text-purple-600">{(cbet_river_pct ?? 0).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 mt-1">Optimal: ~40%</p>
        </div>
      </div>
      <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm">
        <p className="font-medium text-gray-700">Aggression Interpretation:</p>
        <p className="text-gray-600 mt-1">
          {avgDecline < 10 && 'Very persistent with aggression - rarely gives up'}
          {avgDecline >= 10 && avgDecline < 20 && 'Good aggression consistency - balanced barrel frequency'}
          {avgDecline >= 20 && avgDecline < 30 && 'Gives up frequently on later streets - exploitable with floats'}
          {avgDecline >= 30 && 'Gives up too easily - rarely triple barrels (very exploitable)'}
        </p>
      </div>
    </div>
  );
};

export default CBetStreetsChart;
