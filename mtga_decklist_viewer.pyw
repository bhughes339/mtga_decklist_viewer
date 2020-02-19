#!/usr/bin/env python3

import copy
import re
import sys
import os
from tkinter import * # pylint: disable=unused-wildcard-import

import pyperclip
from mtga import all_mtga_cards
from PIL import Image, ImageTk

from mtga_utils import mtga_log

class MtgaLog(mtga_log.MtgaLog):
    
    def get_log_object(self, keyword):
        return self.get_last_json_block('<== ' + keyword)


class DecklistGui:

    RARITIES = ['Common', 'Uncommon', 'Rare', 'Mythic Rare']

    COLORS = {
        'Common': '#000000',
        'Uncommon': '#888888',
        'Rare': '#bea516',
        'Mythic Rare': '#be1c1c',
        'Dimmed': '#cccccc'
    }

    WILDCARD_KEYS = {
        'Common': 'wcCommon',
        'Uncommon': 'wcUncommon',
        'Rare': 'wcRare',
        'Mythic Rare': 'wcMythic'
    }

    INVENTORY_KEYWORD = "PlayerInventory.GetPlayerInventory"

    def __init__(self):
        root = Tk(className='Decklist viewer')
        root.option_add('*Label.Font', 'Arial 12')
        root.config(padx=5, pady=5)

        decklist_frame = Frame(root)
        decklist_frame.pack(side=TOP, fill=BOTH, expand=1)

        card_frame = Frame(decklist_frame)
        card_frame.pack(side=LEFT, padx=(0, 5), fill=BOTH, expand=1)

        Label(card_frame, text='Missing cards:').pack(side=TOP, anchor='nw')

        self.text = Text(card_frame, width=40, height=30, font='Arial 10', state=DISABLED)
        self.text.pack(side=TOP, anchor='w', fill=BOTH, expand=1)

        side_frame = Frame(decklist_frame)
        side_frame.option_add('*Label.Foreground', self.COLORS['Dimmed'])
        side_frame.pack(side=LEFT, fill=Y)

        wildcards = LabelFrame(side_frame, text='Wildcards needed')
        wildcards.pack(side=TOP)

        self.wildcard_labels = {}

        images = {}

        for r in self.RARITIES:
            working_dir = os.path.split(os.path.realpath(__file__))[0]
            imagename = '{0}.png'.format(r.replace(' ','_').lower())
            filename = os.path.join(working_dir, 'images', imagename)
            self.text.tag_config(r.split(' ')[0], font='Arial 10 bold', foreground=self.COLORS[r])
            images[r] = ImageTk.PhotoImage(Image.open(filename).resize((31,26), resample=Image.BILINEAR))
            frame = Frame(wildcards)
            frame.pack(side=TOP, anchor='w')
            Label(frame, image=images[r]).pack(side=LEFT)
            self.wildcard_labels[r] = Label(frame, text='0 (0)')
            self.wildcard_labels[r].pack(side=LEFT, anchor='s')
        
        self.text.tag_config('safe_set', background='#dbffe5')

        control_frame = Frame(side_frame)
        control_frame.pack(side=BOTTOM)

        self.land_ignore = IntVar()
        Checkbutton(control_frame, text="Ignore lands", variable=self.land_ignore).pack(side=TOP, anchor='w')

        self.sideboard_ignore = IntVar(value=1)
        Checkbutton(control_frame, text="Ignore sideboard", variable=self.sideboard_ignore).pack(side=TOP, anchor='w')

        self.get_button = Button(control_frame, text='Get from clipboard', state=DISABLED, command=self.from_clipboard)
        self.get_button.pack(side=TOP)

        rank_frame = Frame(root)
        rank_frame.pack(side=TOP, anchor='w')

        self.rank_info = {
            'constructed': StringVar(value='Constructed: 0W 0L'),
            'limited': StringVar(value='Limited: 0W 0L')
        }
        Label(rank_frame, textvariable=self.rank_info['constructed'], fg='black').pack(side=TOP, anchor='w')
        Label(rank_frame, textvariable=self.rank_info['limited'], fg='black').pack(side=TOP, anchor='w')

        root.update()
        root.minsize(root.winfo_width(), root.winfo_height())

        self.log = None
        self.collection = None
        self.inventory = None

        self.get_safe_sets()

        root.after_idle(self.read_collection)

        root.mainloop()

    def from_clipboard(self):
        self.text.config(state=NORMAL)
        self.find_missing_cards()
        self.text.config(state=DISABLED)

    def read_collection(self):
        self.log = MtgaLog(mtga_log.MTGA_WINDOWS_LOG_FILE)
        rank_info = self.log.get_log_object('Event.GetCombinedRankInfo')['payload']
        self.rank_info['constructed'].set('Constructed: {0}W {1}L ({2} {3})'.format(rank_info['constructedMatchesWon'],
                                                                                    rank_info['constructedMatchesLost'],
                                                                                    rank_info['constructedClass'],
                                                                                    rank_info['constructedLevel']))
        self.rank_info['limited'].set('Limited: {0}W {1}L ({2} {3})'.format(rank_info['limitedMatchesWon'],
                                                                            rank_info['limitedMatchesLost'],
                                                                            rank_info['limitedClass'],
                                                                            rank_info['limitedLevel']))
        self.inventory = self.log.get_inventory()
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
            self.update_wildcards()
        else:
            self.get_button.config(text='Error reading MTGA log')

    def update_wildcards(self, missing_cards={r:{} for r in RARITIES}):
        for r in self.RARITIES:
            count = sum([v['needed'] for k, v in missing_cards[r].items()])
            # stored = int(self.inventory[self.WILDCARD_KEYS[r]])
            stored = int(self.inventory.wildcards[r])
            self.wildcard_labels[r].config(text='{0} ({1})'.format(count, stored), fg='red' if count > stored else 'black')

    def find_missing_cards(self):
        decklist = pyperclip.paste()
        missing_cards = dict([(x, dict()) for x in self.RARITIES])
        card_found = False
        sideboard = False
        for line in decklist.splitlines():
            if not line.strip():
                if card_found and not sideboard:
                    if self.sideboard_ignore.get() == 1:
                        break
                    sideboard = True
                continue
            try:
                req, card = line.strip().lower().split(' ', 1)
            except:
                print('Card parse error: ' + line)
                continue
            card_found = True
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
                owned = self.collection.get(mtga_card.pretty_name, 0)
                needed = int(req) - owned
                name, rarity, set_id = (mtga_card.pretty_name, mtga_card.rarity, mtga_card.set)
                if needed > 0:
                    missing_cards[rarity][name] = missing_cards[rarity].get(name, {'set': set_id})
                    missing_cards[rarity][name]['needed'] = missing_cards[rarity][name].get('needed', 0) + needed
        self.update_text(missing_cards)
        self.update_wildcards(missing_cards)

    def update_text(self, missing_cards):
        self.text.delete('1.0', END)
        for r in self.RARITIES:
            for k, v in missing_cards[r].items():
                tags = (r.split(' ')[0], 'safe_set') if v['set'] in self.safe_sets else r.split(' ')[0]
                self.text.insert(INSERT, f"{v['needed']} {k} ({v['set']})\n", tags)
    

    def get_safe_sets(self):
        import requests, datetime
        this_year = int(datetime.datetime.now().year)
        self.safe_sets = []
        r = requests.get('https://whatsinstandard.com/api/v6/standard.json')
        if r.status_code != requests.codes['ok']:
            return
        payload = r.json()
        for i in payload['sets']:
            match = re.search(r'\d{4}', i['exitDate']['rough'])
            if match:
                if int(match[0]) > this_year and i['code']:
                    self.safe_sets.append(i['code'])


def main():
    DecklistGui()


if __name__ == "__main__":
    main()