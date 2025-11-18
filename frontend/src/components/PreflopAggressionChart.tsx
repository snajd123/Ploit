import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface PreflopAggressionChartProps {
  vpip_pct?: number | null;
  pfr_pct?: number | null;
  three_bet_pct?: number | null;
  limp_pct?: number | null;
}

const PreflopAggressionChart: React.FC<PreflopAggressionChartProps> = ({
  vpip_pct,
  pfr_pct,
  three_bet_pct,
  limp_pct
}) => {
  const data = [
    {
      stat: 'VPIP',
      value: vpip_pct ?? 0,
      hasData: vpip_pct !== null && vpip_pct !== undefined
    },
    {
      stat: 'PFR',
      value: pfr_pct ?? 0,
      hasData: pfr_pct !== null && pfr_pct !== undefined
    },
    {
      stat: '3-Bet',
      value: three_bet_pct ?? 0,
      hasData: three_bet_pct !== null && three_bet_pct !== undefined
    },
    {
      stat: 'Limp',
      value: limp_pct ?? 0,
      hasData: limp_pct !== null && limp_pct !== undefined
    }
  ];

  const gap = (vpip_pct ?? 0) - (pfr_pct ?? 0);

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Preflop Aggression Profile</h3>
      <p className="text-sm text-gray-600 mb-4">
        VPIP/PFR gap: <span className={`font-semibold ${
          gap < 5 ? 'text-green-600' : gap < 10 ? 'text-yellow-600' : 'text-red-600'
        }`}>{gap.toFixed(1)}%</span>
        {' '}
        {gap < 5 && '(Aggressive)'}
        {gap >= 5 && gap < 10 && '(Balanced)'}
        {gap >= 10 && gap < 15 && '(Passive)'}
        {gap >= 15 && '(Very Passive - Calling Station)'}
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="stat" />
          <YAxis label={{ value: 'Frequency %', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(1)}%`}
          />
          <Bar dataKey="value" fill="#3b82f6" name="Frequency">
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-gray-600">VPIP/PFR Gap</p>
          <p className="text-2xl font-bold text-blue-600">{gap.toFixed(1)}%</p>
          <p className="text-xs text-gray-500 mt-1">Lower gap = more aggressive</p>
        </div>
        <div className="p-3 bg-purple-50 rounded-lg">
          <p className="text-gray-600">3-Bet Frequency</p>
          <p className="text-2xl font-bold text-purple-600">{(three_bet_pct ?? 0).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 mt-1">Optimal: 6-10%</p>
        </div>
      </div>
    </div>
  );
};

export default PreflopAggressionChart;
