from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Set
import numpy as np
from dataclasses import dataclass
import sqlite3
from datetime import datetime, timedelta
import json
from pathlib import Path

@dataclass
class Event:
    id: str
    timestamp: datetime
    event_type: str
    key_or_button: str
    position_x: float
    position_y: float
    active_app: str

@dataclass
class Pattern:
    sequence: Tuple[Event, ...]
    frequency: int
    confidence: float
    avg_duration: float
    last_seen: datetime
    app_context: str  # The application where this pattern occurs

class PatternMiner:
    def __init__(self, jsonl_path: str, window_size: int = 10000, min_pattern_length: int = 2, 
                 max_pattern_length: int = 10, min_confidence: float = 0.7,
                 position_threshold: float = 50.0):  # Threshold for considering positions similar
        self.jsonl_path = jsonl_path
        self.window_size = window_size
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
        self.min_confidence = min_confidence
        self.position_threshold = position_threshold
        self.patterns: Dict[Tuple[Event, ...], Pattern] = {}
        
    def _load_events(self) -> List[Event]:
        """Load events from JSONL file."""
        events = []
        with open(self.jsonl_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                events.append(Event(
                    id=data['id'],
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    event_type=data['event_type'],
                    key_or_button=data['key_or_button'],
                    position_x=data['position_x'],
                    position_y=data['position_y'],
                    active_app=data['active_app']
                ))
        return events

    def _get_events_window(self, events: List[Event], offset: int = 0) -> List[Event]:
        """Get a window of events."""
        start = offset
        end = min(start + self.window_size, len(events))
        return events[start:end]

    def _are_positions_similar(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> bool:
        """Check if two positions are similar within threshold."""
        return (abs(pos1[0] - pos2[0]) < self.position_threshold and 
                abs(pos1[1] - pos2[1]) < self.position_threshold)

    def _are_events_similar(self, e1: Event, e2: Event) -> bool:
        """Check if two events are similar enough to be considered the same pattern."""
        if e1.event_type != e2.event_type:
            return False
        if e1.key_or_button != e2.key_or_button:
            return False
        if e1.active_app != e2.active_app:
            return False
        if e1.event_type == 'mouse_click':
            return self._are_positions_similar((e1.position_x, e1.position_y), 
                                            (e2.position_x, e2.position_y))
        return True

    def _calculate_pattern_confidence(self, pattern: Tuple[Event, ...], frequency: int, 
                                    total_windows: int) -> float:
        """Calculate confidence score for a pattern."""
        # Base confidence on frequency
        freq_confidence = frequency / total_windows
        
        # Penalize longer patterns (they're less likely to be random)
        length_penalty = 1.0 - (len(pattern) / self.max_pattern_length)
        
        # Boost confidence for patterns with consistent app context
        app_consistency = 1.0 if all(e.active_app == pattern[0].active_app for e in pattern) else 0.5
        
        # Combine factors
        confidence = freq_confidence * (1.0 + length_penalty) * app_consistency
        return min(confidence, 1.0)

    def _find_patterns_in_window(self, window: List[Event]) -> Dict[Tuple[Event, ...], int]:
        """Find all possible patterns in a single window."""
        patterns = defaultdict(int)
        
        for length in range(self.min_pattern_length, min(self.max_pattern_length + 1, len(window) + 1)):
            for i in range(len(window) - length + 1):
                pattern = tuple(window[i:i + length])
                patterns[pattern] += 1
                
        return patterns

    def _validate_pattern(self, pattern: Tuple[Event, ...], windows: List[List[Event]]) -> bool:
        """Validate if a pattern is meaningful."""
        # Check if pattern appears consistently
        appearances = 0
        for window in windows:
            for i in range(len(window) - len(pattern) + 1):
                if all(self._are_events_similar(pattern[j], window[i+j]) for j in range(len(pattern))):
                    appearances += 1
        consistency = appearances / len(windows)
        
        # Check if pattern has meaningful transitions
        transitions = set()
        for window in windows:
            for i in range(len(window) - len(pattern) + 1):
                if all(self._are_events_similar(pattern[j], window[i+j]) for j in range(len(pattern))):
                    if i > 0:
                        transitions.add(window[i-1].event_type)
                    if i + len(pattern) < len(window):
                        transitions.add(window[i + len(pattern)].event_type)
        
        # Pattern is valid if it appears consistently and has meaningful transitions
        return consistency >= 0.5 and len(transitions) >= 2

    def mine_patterns(self) -> List[Pattern]:
        """Mine patterns from the event database using sliding windows."""
        events = self._load_events()
        all_patterns = defaultdict(int)
        total_windows = 0
        windows = []
        
        # Process windows with overlap
        for offset in range(0, len(events), self.window_size // 2):
            window = self._get_events_window(events, offset)
            if not window:
                break
                
            windows.append(window)
            window_patterns = self._find_patterns_in_window(window)
            
            for pattern, count in window_patterns.items():
                all_patterns[pattern] += count
                
            total_windows += 1

        # Process and validate patterns
        valid_patterns = []
        for pattern, frequency in all_patterns.items():
            if self._validate_pattern(pattern, windows):
                confidence = self._calculate_pattern_confidence(pattern, frequency, total_windows)
                if confidence >= self.min_confidence:
                    # Calculate average duration
                    durations = []
                    for window in windows:
                        for i in range(len(window) - len(pattern) + 1):
                            if all(self._are_events_similar(pattern[j], window[i+j]) for j in range(len(pattern))):
                                start_time = window[i].timestamp
                                end_time = window[i + len(pattern) - 1].timestamp
                                durations.append((end_time - start_time).total_seconds())
                    
                    avg_duration = np.mean(durations) if durations else 0
                    last_seen = max(e.timestamp for e in pattern)
                    app_context = pattern[0].active_app
                    
                    valid_patterns.append(Pattern(
                        sequence=pattern,
                        frequency=frequency,
                        confidence=confidence,
                        avg_duration=avg_duration,
                        last_seen=last_seen,
                        app_context=app_context
                    ))

        # Sort patterns by confidence and frequency
        valid_patterns.sort(key=lambda p: (p.confidence, p.frequency), reverse=True)
        return valid_patterns

    def get_top_patterns(self, limit: int = 10) -> List[Pattern]:
        """Get the top N patterns by confidence and frequency."""
        patterns = self.mine_patterns()
        return patterns[:limit]

    def save_patterns(self, patterns: List[Pattern]):
        """Save discovered patterns to the database."""
        conn = sqlite3.connect('patterns.db')
        cursor = conn.cursor()
        
        # Create patterns table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                confidence REAL NOT NULL,
                avg_duration REAL NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                app_context TEXT NOT NULL
            )
        """)
        
        # Clear existing patterns
        cursor.execute("DELETE FROM patterns")
        
        # Insert new patterns
        for pattern in patterns:
            sequence_str = json.dumps([{
                'event_type': e.event_type,
                'key_or_button': e.key_or_button,
                'position_x': e.position_x,
                'position_y': e.position_y,
                'active_app': e.active_app
            } for e in pattern.sequence])
            
            cursor.execute("""
                INSERT INTO patterns (sequence, frequency, confidence, avg_duration, last_seen, app_context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sequence_str,
                pattern.frequency,
                pattern.confidence,
                pattern.avg_duration,
                pattern.last_seen.isoformat(),
                pattern.app_context
            ))
        
        conn.commit()
        conn.close()
