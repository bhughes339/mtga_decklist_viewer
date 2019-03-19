#!/usr/bin/env python3

import copy
import re
import sys
from tkinter import *

import pyperclip
from mtga import all_mtga_cards

from mtga_utils import mtga_log

RARITIES = ['Common', 'Uncommon', 'Rare', 'Mythic Rare']

COLORS = {
    'Common': '#000000',
    'Uncommon': '#888888',
    'Rare': '#bea516',
    'Mythic Rare': '#be1c1c',
    'Dimmed': '#cccccc'
}

INVENTORY_KEYS = {
    'Common': 'wcCommon',
    'Uncommon': 'wcUncommon',
    'Rare': 'wcRare',
    'Mythic Rare': 'wcMythic'
}

INVENTORY_KEYWORD = "PlayerInventory.GetPlayerInventory"

class MtgaLog(mtga_log.MtgaLog):
    
    def get_log_object(self, keyword):
        return self.get_last_json_block('<== ' + keyword)


class DecklistGui:

    def __init__(self):
        root = Tk(className='Decklist viewer')
        root.option_add('*Label.Font', 'Arial 12')
        root.config(padx=5, pady=5)

        card_frame = Frame(root)
        card_frame.pack(side=LEFT, padx=(0, 5), fill=BOTH, expand=1)

        Label(card_frame, text='Missing cards:').pack(side=TOP, anchor='nw')

        self.text = Text(card_frame, width=40, height=20, font='Arial 10', state=DISABLED)
        self.text.pack(side=TOP, anchor='w', fill=BOTH, expand=1)

        deck_cost_frame = Frame(card_frame)
        Label(deck_cost_frame, text='Total wildcard cost:').pack(side=LEFT)
        deck_cost_frame.pack(side=TOP, anchor='w')

        side_frame = Frame(root)
        side_frame.option_add('*Label.Foreground', COLORS['Dimmed'])
        side_frame.pack(side=LEFT, fill=Y)

        self.deck_costs = {}

        wildcards = LabelFrame(side_frame, text='Wildcards needed')
        wildcards.pack(side=TOP)

        self.wildcard_labels = {}

        for r in RARITIES:
            self.text.tag_config(r.split(' ')[0], font='Arial 10 bold', foreground=COLORS[r])
            self.wildcard_labels[r] = Label(wildcards, text='0 {0}'.format(r))
            self.wildcard_labels[r].pack(side=TOP, padx=5)
            self.deck_costs[r] = Label(deck_cost_frame, text='0', foreground=COLORS[r])
            self.deck_costs[r].pack(side=LEFT)

        control_frame = Frame(side_frame)
        control_frame.pack(side=BOTTOM)

        self.land_ignore = IntVar()
        Checkbutton(control_frame, text="Ignore lands", variable=self.land_ignore).pack(side=TOP)

        self.sideboard_ignore = IntVar()
        Checkbutton(control_frame, text="Ignore sideboard", variable=self.sideboard_ignore).pack(side=TOP)

        self.get_button = Button(control_frame, text='Get from clipboard', state=DISABLED, command=self.from_clipboard)
        self.get_button.pack(side=TOP)

        self.log = None
        self.collection = None
        self.inventory = None
        root.after(100, self.read_collection)

        root.mainloop()

    def from_clipboard(self):
        self.text.config(state=NORMAL)
        try:
            self.find_missing_cards()
        except:
            pass
        self.text.config(state=DISABLED)

    def read_collection(self):
        self.log = MtgaLog(mtga_log.MTGA_WINDOWS_LOG_FILE)
        self.inventory = self.log.get_log_object(INVENTORY_KEYWORD)
        collection = {}
        for c in self.log.get_collection():
            # c format: [mtga_id, Card object, count]
            name = c[1].pretty_name
            try:
                collection[name] += int(c[2])
            except:
                collection[name] = int(c[2])
        self.collection = collection
        if len(collection) > 0:
            self.get_button.config(state=NORMAL)
        else:
            self.get_button.config(text='Error reading MTGA log')

    def update_wildcards(self, missing_cards):
        for r in RARITIES:
            count = sum([v for k, v in missing_cards[r].items()])
            needed = max(count - int(self.inventory[INVENTORY_KEYS[r]]), 0)
            self.wildcard_labels[r].config(text='{0} {1}'.format(needed, r), fg=COLORS['Dimmed' if needed == 0 else r])
            self.deck_costs[r].config(text=count)

    def find_missing_cards(self):
        decklist = pyperclip.paste()
        missing_cards = dict([(x, dict()) for x in RARITIES])
        card_found = False
        sideboard = False
        for line in decklist.split('\n'):
            if not line.strip():
                if card_found and not sideboard:
                    if self.sideboard_ignore.get() == 1:
                        break
                    sideboard = True
                continue
            card_found = True
            req, card = line.strip().lower().split(' ', 1)
            card = re.sub(r' \(.*', '', card)
            card = re.sub(r' +', '_', card)
            card = re.sub(r'[^a-z_]', '', card)
            search = all_mtga_cards.search(card, True)
            if len(search) < 1:
                print('Could not find card: ' + card)
                continue
            mtga_card = search[0]
            if 'basic' not in mtga_card.rarity.lower():
                if self.land_ignore.get() == 1 and mtga_card.card_type == 'Land':
                    continue
                try:
                    owned = self.collection[mtga_card.pretty_name]
                except:
                    owned = 0
                needed = int(req) - owned
                if needed > 0:
                    try:
                        missing_cards[mtga_card.rarity][mtga_card.pretty_name] += needed
                    except:
                        missing_cards[mtga_card.rarity][mtga_card.pretty_name] = needed
        self.update_text(missing_cards)
        self.update_wildcards(missing_cards)

    def update_text(self, missing_cards):
        self.text.delete('1.0', END)
        for r in RARITIES:
            for k, v in missing_cards[r].items():
                self.text.insert(INSERT, '{0} {1}\n'.format(v, k), r.split(' ')[0])


def main():
    DecklistGui()


if __name__ == "__main__":
    main()
