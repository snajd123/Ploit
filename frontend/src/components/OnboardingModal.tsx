import { useState, useEffect } from 'react';
import { X, Upload, Users, Target, ChevronRight, ChevronLeft, CheckCircle } from 'lucide-react';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ONBOARDING_COMPLETE_KEY = 'poker-onboarding-complete';

const steps = [
  {
    title: 'Upload Your Hand Histories',
    description: 'Start by uploading your PokerStars hand history files. The platform will parse all hands, track player statistics, and calculate advanced metrics automatically.',
    icon: Upload,
    color: 'blue',
    tips: [
      'Export hand histories from PokerStars (Request My Data)',
      'Multiple files can be uploaded at once',
      'Sessions will be auto-detected after upload'
    ]
  },
  {
    title: 'Review Players & Sessions',
    description: 'Browse player statistics to understand their tendencies. Check your session history to track your own performance and identify areas for improvement.',
    icon: Users,
    color: 'green',
    tips: [
      'Filter players by type (TAG, LAG, Fish, etc.)',
      'View detailed stats like VPIP, PFR, 3-bet%',
      'Analyze your sessions with GTO comparison'
    ]
  },
  {
    title: 'Generate Exploit Strategies',
    description: 'Use AI-powered strategy generation to create personalized game plans against specific opponents. Get actionable tips before your next session.',
    icon: Target,
    color: 'purple',
    tips: [
      'Generate pre-game strategies for opponents',
      'Compare your play vs GTO baselines',
      'Ask Claude AI for deeper analysis'
    ]
  }
];

const OnboardingModal: React.FC<OnboardingModalProps> = ({ isOpen, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);

  // Reset to first step when modal opens
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
    }
  }, [isOpen]);

  const handleComplete = () => {
    localStorage.setItem(ONBOARDING_COMPLETE_KEY, 'true');
    onClose();
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  if (!isOpen) return null;

  const step = steps[currentStep];
  const StepIcon = step.icon;
  const isLastStep = currentStep === steps.length - 1;

  const colorClasses = {
    blue: {
      bg: 'bg-blue-100',
      icon: 'text-blue-600',
      border: 'border-blue-200',
      dot: 'bg-blue-600'
    },
    green: {
      bg: 'bg-green-100',
      icon: 'text-green-600',
      border: 'border-green-200',
      dot: 'bg-green-600'
    },
    purple: {
      bg: 'bg-purple-100',
      icon: 'text-purple-600',
      border: 'border-purple-200',
      dot: 'bg-purple-600'
    }
  };

  const colors = colorClasses[step.color as keyof typeof colorClasses];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 z-10"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <div className={`p-8 ${colors.bg}`}>
          <div className={`w-16 h-16 ${colors.bg} border-2 ${colors.border} rounded-2xl flex items-center justify-center mx-auto`}>
            <StepIcon size={32} className={colors.icon} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 text-center mt-4">
            {step.title}
          </h2>
        </div>

        {/* Content */}
        <div className="p-8">
          <p className="text-gray-600 text-center mb-6">
            {step.description}
          </p>

          {/* Tips */}
          <div className="space-y-3">
            {step.tips.map((tip, index) => (
              <div key={index} className="flex items-start gap-3">
                <CheckCircle size={18} className={`${colors.icon} flex-shrink-0 mt-0.5`} />
                <span className="text-sm text-gray-700">{tip}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 pb-8">
          {/* Progress dots */}
          <div className="flex justify-center gap-2 mb-6">
            {steps.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentStep(index)}
                className={`w-2.5 h-2.5 rounded-full transition-all ${
                  index === currentStep
                    ? `${colors.dot} w-6`
                    : 'bg-gray-300 hover:bg-gray-400'
                }`}
              />
            ))}
          </div>

          {/* Navigation buttons */}
          <div className="flex gap-3">
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <ChevronLeft size={18} />
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-colors ${
                currentStep === 0 ? 'w-full' : ''
              }`}
            >
              {isLastStep ? "Get Started" : "Next"}
              {!isLastStep && <ChevronRight size={18} />}
            </button>
          </div>

          {/* Skip option */}
          <button
            onClick={handleComplete}
            className="w-full mt-3 text-sm text-gray-500 hover:text-gray-700"
          >
            Skip tutorial
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper to check if onboarding should show
export const shouldShowOnboarding = (): boolean => {
  return localStorage.getItem(ONBOARDING_COMPLETE_KEY) !== 'true';
};

// Helper to reset onboarding (for "Show Tutorial" button)
export const resetOnboarding = (): void => {
  localStorage.removeItem(ONBOARDING_COMPLETE_KEY);
};

export default OnboardingModal;
