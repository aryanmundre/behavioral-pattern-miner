from collections import Counter

def find_frequent_sequences(sessions, min_occurrences=2):
    sequence_counter = Counter()

    for session in sessions:
        if len(session) >= 2:
            for i in range(len(session) - 1):
                pair = (session[i], session[i+1])
                sequence_counter[pair] += 1

    frequent_sequences = [seq for seq, count in sequence_counter.items() if count >= min_occurrences]
    return frequent_sequences
