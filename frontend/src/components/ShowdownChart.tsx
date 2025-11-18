import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface ShowdownChartProps {
  wtsd_pct?: number | null;
  wsd_pct?: number | null;
}

const ShowdownChart: React.FC<ShowdownChartProps> = ({ wtsd_pct, wsd_pct }) => {
  const wtsd = wtsd_pct ?? 0;
  const wsd = wsd_pct ?? 0;

  // WTSD interpretation
  const wtsdInterpretation = wtsd < 20 ? 'Tight/Folding' : wtsd < 28 ? 'Optimal' : wtsd < 35 ? 'Loose' : 'Very Loose';
  const wtsdColor = wtsd < 20 ? '#ef4444' : wtsd < 28 ? '#10b981' : wtsd < 35 ? '#f59e0b' : '#ef4444';

  // W$SD interpretation
  const wsdInterpretation = wsd < 45 ? 'Weak Hands' : wsd < 55 ? 'Optimal' : 'Strong Hands';
  const wsdColor = wsd < 45 ? '#ef4444' : wsd < 55 ? '#10b981' : '#3b82f6';

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Showdown Performance</h3>
      <p className="text-sm text-gray-600 mb-4">
        Showdown frequency and win rate when hands go to showdown
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* WTSD */}
        <div>
          <div className="text-center mb-4">
            <p className="text-sm text-gray-600">Went To Showdown %</p>
            <p className="text-4xl font-bold mt-1" style={{ color: wtsdColor }}>
              {wtsd.toFixed(1)}%
            </p>
            <p className="text-sm font-medium mt-1" style={{ color: wtsdColor }}>
              {wtsdInterpretation}
            </p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-700 mb-2">Interpretation:</p>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>• &lt;20%: Folds too much, exploitable with bluffs</li>
              <li>• 20-28%: Optimal showdown frequency</li>
              <li>• 28-35%: Goes to showdown too often</li>
              <li>• &gt;35%: Calling station - value bet thin</li>
            </ul>
          </div>
        </div>

        {/* W$SD */}
        <div>
          <div className="text-center mb-4">
            <p className="text-sm text-gray-600">Won $ at Showdown %</p>
            <p className="text-4xl font-bold mt-1" style={{ color: wsdColor }}>
              {wsd.toFixed(1)}%
            </p>
            <p className="text-sm font-medium mt-1" style={{ color: wsdColor }}>
              {wsdInterpretation}
            </p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-700 mb-2">Interpretation:</p>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>• &lt;45%: Going to showdown with weak hands</li>
              <li>• 45-55%: Optimal hand strength at showdown</li>
              <li>• &gt;55%: Only showing down strong hands</li>
              <li>• Combined with high WTSD = station</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Exploitation guide */}
      <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <p className="text-sm font-semibold text-gray-900 mb-2">Exploitation Strategy:</p>
        <p className="text-sm text-gray-700">
          {wtsd > 30 && wsd < 50 && (
            <>
              <span className="font-medium text-red-600">Calling Station!</span> Goes to showdown too often with weak hands.
              <span className="font-semibold"> Value bet thin, don't bluff.</span>
            </>
          )}
          {wtsd < 20 && (
            <>
              <span className="font-medium text-orange-600">Folds too much!</span> Rarely goes to showdown.
              <span className="font-semibold"> Bluff frequently on turn/river.</span>
            </>
          )}
          {wtsd >= 20 && wtsd <= 30 && wsd >= 45 && wsd <= 55 && (
            <>
              <span className="font-medium text-green-600">Balanced player.</span> Optimal showdown frequencies.
              <span className="font-semibold"> Look for other exploits.</span>
            </>
          )}
          {wsd > 55 && wtsd < 25 && (
            <>
              <span className="font-medium text-blue-600">Tight/Nitty.</span> Only shows down strong hands.
              <span className="font-semibold"> Don't pay them off, steal their blinds.</span>
            </>
          )}
          {wtsd > 25 && wtsd < 35 && wsd >= 50 && (
            <>
              <span className="font-medium text-yellow-600">Slightly loose.</span> Goes to showdown a bit too often but wins decent.
              <span className="font-semibold"> Value bet moderately.</span>
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export default ShowdownChart;
