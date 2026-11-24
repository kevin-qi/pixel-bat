"""Cards of the pairs Kilosort tests directly (each unit of a proposed group against its largest unit), copied in batches for
review: merge_stage.py SESSIONS_CSV NAME REVIEW_DIR STAGE_DIR. Prints the batch folders."""
import json
import os
import shutil
import sys

import pandas as pd

sessions = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False).set_index('name')
name, review, stage = sys.argv[2:5]
proposed = json.load(open(os.path.join(sessions.loc[name, 'sort'], 'proposed_merges.json')))
# A card is named with the pair's larger unit first, by the spike counts of the finished sort
rendered = pd.read_csv(os.path.join(review, 'similarity', f'{name}.csv'))
card_of = {frozenset([a, b]): f'{name}_{a}_{b}.png' for a, b in zip(rendered['a'], rendered['b'])}
cards = []
for group in proposed['groups']:
    largest = max(group, key=lambda unit: proposed['spikes_per_unit'][str(unit)])
    for unit in group:
        if unit != largest:
            cards.append(card_of[frozenset([largest, unit])])
for start in range(0, len(cards), 50):
    folder = os.path.join(stage, name, f'part{start // 50}')
    os.makedirs(folder)
    for card in cards[start:start + 50]:
        shutil.copy(os.path.join(review, 'cards', card), folder)
    print(folder, len(cards[start:start + 50]))
