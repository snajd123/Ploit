import { ReactNode, useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface TooltipProps {
  content: ReactNode;
  children?: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  showIcon?: boolean;
  iconSize?: number;
}

export const Tooltip = ({
  content,
  children,
  position = 'top',
  showIcon: _showIcon = true,
  iconSize = 16
}: TooltipProps) => {
  const [isVisible, setIsVisible] = useState(false);

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div className="relative inline-flex items-center group">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        className="cursor-help"
      >
        {children || (
          <HelpCircle
            size={iconSize}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          />
        )}
      </div>

      {isVisible && (
        <div
          className={`absolute z-50 ${positionClasses[position]} animate-fadeIn`}
          style={{ width: 'max-content', maxWidth: '300px' }}
        >
          <div className="bg-gray-900 text-white text-sm rounded-lg px-3 py-2 shadow-lg">
            {content}
            {/* Arrow */}
            <div
              className={`absolute w-2 h-2 bg-gray-900 transform rotate-45 ${
                position === 'top' ? 'bottom-[-4px] left-1/2 -translate-x-1/2' :
                position === 'bottom' ? 'top-[-4px] left-1/2 -translate-x-1/2' :
                position === 'left' ? 'right-[-4px] top-1/2 -translate-y-1/2' :
                'left-[-4px] top-1/2 -translate-y-1/2'
              }`}
            />
          </div>
        </div>
      )}
    </div>
  );
};

interface StatTooltipProps {
  stat: string;
  value?: number;
  description: string;
  formula?: string;
  optimal?: [number, number] | null;
  interpretation?: string;
}

export const StatTooltip = ({
  stat,
  value,
  description,
  formula,
  optimal,
  interpretation
}: StatTooltipProps) => {
  return (
    <Tooltip
      content={
        <div className="space-y-2">
          <div>
            <div className="font-semibold text-blue-300">{stat}</div>
            <div className="text-xs text-gray-300 mt-1">{description}</div>
          </div>

          {formula && (
            <div className="text-xs border-t border-gray-700 pt-2">
              <div className="text-gray-400">Formula:</div>
              <code className="text-gray-200 font-mono text-xs">{formula}</code>
            </div>
          )}

          {optimal && (
            <div className="text-xs border-t border-gray-700 pt-2">
              <div className="text-gray-400">Optimal Range:</div>
              <div className="text-green-300 font-medium">{optimal[0]}% - {optimal[1]}%</div>
            </div>
          )}

          {value !== undefined && interpretation && (
            <div className="text-xs border-t border-gray-700 pt-2">
              <div className="text-gray-400">Current ({value}%):</div>
              <div className="text-yellow-300">{interpretation}</div>
            </div>
          )}
        </div>
      }
      position="top"
    />
  );
};

export default Tooltip;
