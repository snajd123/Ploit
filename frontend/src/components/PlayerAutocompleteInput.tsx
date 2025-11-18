/**
 * PlayerAutocompleteInput Component
 *
 * Autocomplete input for player names with comma-separated support
 */

import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check } from 'lucide-react';
import { api } from '../services/api';
import type { PlayerListItem } from '../types';

interface PlayerAutocompleteInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const PlayerAutocompleteInput: React.FC<PlayerAutocompleteInputProps> = ({
  value,
  onChange,
  placeholder = 'Start typing player names...',
  className = ''
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [currentInput, setCurrentInput] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch all players
  const { data: players } = useQuery({
    queryKey: ['players'],
    queryFn: () => api.getPlayers(),
  });

  // Get the current word being typed (after the last comma)
  useEffect(() => {
    const lastCommaIndex = value.lastIndexOf(',');
    const current = value.slice(lastCommaIndex + 1).trim();
    setCurrentInput(current);
  }, [value]);

  // Filter players based on current input
  const filteredPlayers = players
    ?.filter((p: PlayerListItem) => {
      if (!currentInput) return false;
      const alreadyAdded = value
        .split(',')
        .map((n: string) => n.trim().toLowerCase())
        .filter((n: string) => n.length > 0);
      const isAlreadyAdded = alreadyAdded.includes(p.player_name.toLowerCase());
      return (
        !isAlreadyAdded &&
        p.player_name.toLowerCase().includes(currentInput.toLowerCase())
      );
    })
    .slice(0, 8) || []; // Limit to 8 suggestions

  // Show dropdown when there are suggestions
  useEffect(() => {
    setShowDropdown(filteredPlayers.length > 0);
    setSelectedIndex(0);
  }, [filteredPlayers.length]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectPlayer = (playerName: string) => {
    const lastCommaIndex = value.lastIndexOf(',');
    let newValue;

    if (lastCommaIndex === -1) {
      // First player
      newValue = `${playerName}, `;
    } else {
      // Add to existing list
      const before = value.slice(0, lastCommaIndex + 1);
      newValue = `${before} ${playerName}, `;
    }

    onChange(newValue);
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || filteredPlayers.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev =>
          prev < filteredPlayers.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : 0);
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredPlayers[selectedIndex]) {
          handleSelectPlayer(filteredPlayers[selectedIndex].player_name);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setShowDropdown(false);
        break;
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (filteredPlayers.length > 0) setShowDropdown(true);
        }}
        placeholder={placeholder}
        className={className}
      />

      {/* Autocomplete Dropdown */}
      {showDropdown && filteredPlayers.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-64 overflow-y-auto"
        >
          {filteredPlayers.map((player: PlayerListItem, idx: number) => (
            <button
              key={player.player_name}
              onClick={() => handleSelectPlayer(player.player_name)}
              className={`w-full px-4 py-2 text-left hover:bg-blue-50 flex items-center justify-between transition-colors ${
                idx === selectedIndex ? 'bg-blue-50' : ''
              }`}
            >
              <div>
                <div className="font-medium text-gray-900">{player.player_name}</div>
                <div className="text-xs text-gray-500">
                  {player.total_hands.toLocaleString()} hands
                  {player.player_type && (
                    <span className="ml-2 text-gray-400">• {player.player_type}</span>
                  )}
                </div>
              </div>
              {idx === selectedIndex && (
                <Check className="w-4 h-4 text-blue-600" />
              )}
            </button>
          ))}
        </div>
      )}

      {/* Helper text showing selected players */}
      {value && (
        <div className="mt-2 flex flex-wrap gap-1">
          {value
            .split(',')
            .map(n => n.trim())
            .filter(n => n.length > 0)
            .map((name, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded"
              >
                {name}
              </span>
            ))}
        </div>
      )}
    </div>
  );
};

export default PlayerAutocompleteInput;
