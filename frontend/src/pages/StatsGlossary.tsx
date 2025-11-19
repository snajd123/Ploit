import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, BookOpen } from 'lucide-react';
import { STAT_DEFINITIONS, StatDefinition } from '../config/statDefinitions';

const StatsGlossary = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Get all unique categories
  const categories = ['all', ...new Set(Object.values(STAT_DEFINITIONS).map(stat => stat.category))];

  // Filter stats based on search and category
  const filteredStats = Object.entries(STAT_DEFINITIONS).filter(([_key, stat]) => {
    const matchesSearch = searchQuery === '' ||
      stat.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stat.abbreviation.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stat.description.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory = selectedCategory === 'all' || stat.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  // Group stats by category
  const statsByCategory = filteredStats.reduce((acc, [key, stat]) => {
    if (!acc[stat.category]) {
      acc[stat.category] = [];
    }
    acc[stat.category].push({ key, ...stat });
    return acc;
  }, {} as Record<string, Array<StatDefinition & { key: string }>>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft size={20} />
          <span>Back</span>
        </button>

        <div className="flex items-center space-x-3 mb-2">
          <BookOpen size={32} className="text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Statistics Glossary</h1>
        </div>
        <p className="text-gray-600">
          Complete reference for all poker statistics with formulas, optimal ranges, and interpretations
        </p>
      </div>

      {/* Search and Filter */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search statistics..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Results count */}
        <div className="mt-3 text-sm text-gray-600">
          Showing {filteredStats.length} of {Object.keys(STAT_DEFINITIONS).length} statistics
        </div>
      </div>

      {/* Stats grouped by category */}
      {Object.entries(statsByCategory).map(([category, stats]) => (
        <div key={category} className="space-y-4">
          <h2 className="text-2xl font-semibold text-gray-900 border-b-2 border-blue-600 pb-2">
            {category}
          </h2>

          <div className="grid grid-cols-1 gap-4">
            {stats.map((stat) => (
              <div key={stat.key} className="card hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">{stat.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      <span className="font-medium text-blue-600">{stat.abbreviation}</span>
                      {stat.minSample && (
                        <span className="ml-2">• Min sample: {stat.minSample} hands</span>
                      )}
                    </p>
                  </div>
                  {stat.optimalRange && (
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Optimal Range</p>
                      <p className="text-lg font-bold text-green-600">
                        {stat.optimalRange[0]}{stat.unit} - {stat.optimalRange[1]}{stat.unit}
                      </p>
                    </div>
                  )}
                </div>

                {/* Parse description into sections */}
                {(() => {
                  const sections = stat.description.split(/\n\n(?=Variables:|Example:|Interpretation:|Requirements:|Context:|Note:|Calculation:|Weighting:|Positions and Optimal VPIP:)/);
                  const mainDesc = sections[0];
                  const otherSections = sections.slice(1);

                  // Find variables section
                  const variablesSection = otherSections.find(s => s.startsWith('Variables:'));
                  const nonVariableSections = otherSections.filter(s => !s.startsWith('Variables:'));

                  return (
                    <>
                      <p className="text-gray-700 mb-3 whitespace-pre-line">{mainDesc}</p>

                      {/* Formula */}
                      <div className="bg-gray-50 border border-gray-300 rounded-lg p-3 mb-3">
                        <p className="text-xs font-medium text-gray-700 mb-1">Formula:</p>
                        <code className="text-sm text-gray-900 font-mono whitespace-pre-line">{stat.formula}</code>
                      </div>

                      {/* Variables (if exists) */}
                      {variablesSection && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3">
                          <p className="text-xs font-medium text-amber-900 mb-1">Variables:</p>
                          <div className="text-sm text-gray-900 whitespace-pre-line">
                            {variablesSection.replace('Variables:', '').trim()}
                          </div>
                        </div>
                      )}

                      {/* Other sections */}
                      {nonVariableSections.map((section, idx) => {
                        if (section.startsWith('Example:')) {
                          return (
                            <div key={idx} className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                              <p className="text-xs font-medium text-blue-900 mb-1">Example:</p>
                              <div className="text-sm text-gray-900 whitespace-pre-line">
                                {section.replace('Example:', '').trim()}
                              </div>
                            </div>
                          );
                        } else if (section.startsWith('Interpretation:')) {
                          return (
                            <div key={idx} className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3">
                              <p className="text-xs font-medium text-purple-900 mb-1">Interpretation:</p>
                              <div className="text-sm text-gray-900 whitespace-pre-line">
                                {section.replace('Interpretation:', '').trim()}
                              </div>
                            </div>
                          );
                        } else if (section.startsWith('Requirements:') || section.startsWith('Context:') || section.startsWith('Note:')) {
                          const label = section.split(':')[0] + ':';
                          return (
                            <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
                              <p className="text-xs font-medium text-gray-900 mb-1">{label}</p>
                              <div className="text-sm text-gray-700 whitespace-pre-line">
                                {section.replace(label, '').trim()}
                              </div>
                            </div>
                          );
                        } else if (section.startsWith('Calculation:') || section.startsWith('Weighting:') || section.startsWith('Positions and Optimal VPIP:')) {
                          const label = section.split(':')[0] + ':';
                          return (
                            <div key={idx} className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 mb-3">
                              <p className="text-xs font-medium text-indigo-900 mb-1">{label}</p>
                              <div className="text-sm text-gray-900 whitespace-pre-line">
                                {section.replace(label, '').trim()}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      })}
                    </>
                  );
                })()}

                {/* Tooltip/Quick Reference */}
                <div className="bg-blue-50 border-l-4 border-blue-600 p-3 rounded">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium text-blue-900">Quick Reference: </span>
                    {stat.tooltip}
                  </p>
                </div>

                {/* Interpretation Guide */}
                {stat.interpretationGuide && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-sm font-medium text-gray-700 mb-2">Interpretation Guide:</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {Object.entries(stat.interpretationGuide).map(([range, interpretation]) => (
                        <div key={range} className="text-xs bg-gray-50 rounded px-3 py-2">
                          <span className="font-semibold text-gray-900">{range}: </span>
                          <span className="text-gray-700">{interpretation}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* No results */}
      {filteredStats.length === 0 && (
        <div className="card text-center py-12">
          <Search size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 text-lg">No statistics found matching your search</p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('all');
            }}
            className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Footer info */}
      <div className="card bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">About These Statistics</h3>
        <div className="text-sm text-gray-700 space-y-2">
          <p>
            All statistics are calculated from actual hand history data. The optimal ranges are based on
            modern poker theory and GTO (Game Theory Optimal) principles.
          </p>
          <p>
            <span className="font-medium">Min Sample:</span> The minimum number of hands required for the statistic to be reliable.
            Statistics with fewer hands should be interpreted with caution.
          </p>
          <p>
            <span className="font-medium">Composite Metrics:</span> Advanced statistics that combine multiple traditional stats
            to provide deeper insights into player tendencies and exploitability.
          </p>
        </div>
      </div>
    </div>
  );
};

export default StatsGlossary;
