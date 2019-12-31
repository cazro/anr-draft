#!/usr/bin/env python


import json
import os
import random
import string
import time
import asyncio
import discord

from templates import blocks, templates

HERE = os.path.dirname(os.path.abspath(__file__))
with open(HERE + '/secrets.json', 'r') as f:
    tokens = json.loads(f.read())
    TOKEN = tokens["api_token"]
    
# SLACK METHOD - REPLACE WITH DISCORD RED METHOD
client = discord.Client()

DRAFTS = {}
PLAYERS = {}

# Getters

def get_player_id(player_name):
    if player_name in PLAYERS:
        return PLAYERS[player_name]['player_id']


def get_player_dm_id(player_name):
    return PLAYERS[player_name]['dm_id']


def get_player_draft_info(player_name):
    draft_id = PLAYERS[player_name]['draft_id']
    return DRAFTS[draft_id]['players'][player_name]


def get_seat_number(player_name):
    return PLAYERS[player_name]['seat_number']


def get_num_players(draft_id):
    return len(get_players(draft_id))


def get_players(draft_id):
    return DRAFTS[draft_id]['players'].keys()


def get_creator(draft_id):
    return DRAFTS[draft_id]['metadata']['creator']


def get_pack(draft_id, player_name, pack_num):
    return DRAFTS[draft_id]['players'][player_name]['packs'][pack_num]


def get_picks(draft_id, player_name):
    return DRAFTS[draft_id]['players'][player_name]['picks']


def get_card(card_code):
    data_dir = HERE + '/data'
    corp_ids = read_cards_from_file(data_dir + '/corp_ids.json')
    corp_cards = read_cards_from_file(data_dir + '/corp_cards.json')
    runner_ids = read_cards_from_file(data_dir + '/runner_ids.json')
    runner_cards = read_cards_from_file(data_dir + '/runner_cards.json')
    all_cards = corp_ids+corp_cards+runner_ids+runner_cards

    for card in all_cards:
        if card['code'] == card_code:
            return card


def get_image_url(code):
    data_dir = HERE + '/data'
    filepath = data_dir + '/corp_ids.json'
    with open(filepath, 'r') as f:
        imageUrlTemplate = json.loads(f.read())['imageUrlTemplate']
        return imageUrlTemplate.format(code=code)

def player_has_pack_waiting(draft_id, player_name):
    inbox = DRAFTS[draft_id]['players'][player_name]['inbox']
    return len(inbox) > 0


def player_has_open_pack(draft_id, player_name):
    return DRAFTS[draft_id]['players'][player_name]['has_open_pack']


def draft_finished(draft_id):
    for player in get_players(draft_id):
        inbox = DRAFTS[draft_id]['players'][player]['inbox']
        packs = DRAFTS[draft_id]['players'][player]['packs']
        if len(packs) > 0 or len(inbox) > 0:
            return False
    return True


def draft_started(draft_id):
    return DRAFTS[draft_id]['metadata']['has_started']


def user_can_create_draft(username):
    for draft in DRAFTS:
        if DRAFTS[draft]['metadata']['creator'] == username:
            return False
    return True

# Discord Helpers

async def send_dm(player_id, content,embed=None):
    user = client.get_user(player_id)

    if user.dm_channel:
        dm_channel = user.dm_channel
    else:
        await user.create_dm()
        dm_channel = user.dm_channel

    await dm_channel.send(content=content,embed=embed)


async def send_card(player,card):
    card_text = templates.format(card)
    embedded_card = discord.Embed(title=card['title'])
    embedded_card.description = card_text
    embedded_card.add_field(name='To pick this card:',value='```!pick {code}```'.format(code=card['code']))
    embedded_card.set_image(url=get_image_url(card['code']))

    await send_dm(
        player_id=get_player_id(player),
        content="Card",
        embed=embedded_card
    )


# Draft Setup

def setup_draft(initiating_user_name, initiating_user_id):
    draft_id = gen_draft_id()
    while draft_id in DRAFTS:
        draft_id = gen_draft_id()
    DRAFTS[draft_id] = {
        'metadata': {
            'creator': initiating_user_name,
            'has_started': False,
            'stage': 0
        },
        'players': {}
    }
    add_player(initiating_user_name, initiating_user_id, draft_id)
    return draft_id


def gen_draft_id():
    code = ''
    for _ in range(4):
        total_chars = len(string.ascii_lowercase)
        index = random.randint(0, total_chars - 1)
        letter = string.ascii_lowercase[index]
        code += letter
    return code


def deal_card(draft_id, player_name, pack_num, card):
    DRAFTS[draft_id]["players"][player_name]['packs'][pack_num].append(
        card)


def read_cards_from_file(filepath):
    with open(filepath, 'r') as f:
        cards = json.loads(f.read())['cards']
        return cards


def setup_packs(draft_id):
    num_players = get_num_players(draft_id)
    total_ids = num_players * 5
    card_total = num_players * 15 * 3

    data_dir = HERE + '/data'
    corp_ids = read_cards_from_file(data_dir + '/corp_ids.json')
    random.shuffle(corp_ids)
    corp_ids = corp_ids[:total_ids]
    corp_cards = read_cards_from_file(data_dir + '/corp_cards.json')
    random.shuffle(corp_cards)
    corp_cards = corp_cards[:card_total]
    runner_ids = read_cards_from_file(data_dir + '/runner_ids.json')
    random.shuffle(runner_ids)
    runner_ids = runner_ids[:total_ids]
    runner_cards = read_cards_from_file(data_dir + '/runner_cards.json')
    random.shuffle(runner_cards)
    runner_cards = runner_cards[:card_total]

    pack_num = 0
    cards_per_pack = len(corp_cards) // (get_num_players(draft_id) * 3)
    while len(corp_ids) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(corp_ids) - 1)
            card = corp_ids.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
    pack_num += 1

    while corp_cards and pack_num <= 3:
        for player in get_players(draft_id):
            card_index = random.randint(0, len(corp_cards) - 1)
            card = corp_cards.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
        if len(get_pack(draft_id, player, pack_num)) == cards_per_pack:
            pack_num += 1

    while len(runner_ids) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(runner_ids) - 1)
            card = runner_ids.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
    pack_num += 1

    while len(runner_cards) >= get_num_players(draft_id):
        for player in get_players(draft_id):
            card_index = random.randint(0, len(runner_cards) - 1)
            card = runner_cards.pop(card_index)
            deal_card(draft_id, player, pack_num, card)
        if len(get_pack(draft_id, player, pack_num)) == cards_per_pack:
            pack_num += 1


def add_player(player_name, player_id, draft_id):
    # im_list = client.im_list()
    # for im in im_list['ims']:
        # if im['user'] == player_id:
    if client.get_user(player_id):
        player_dm_id = client.get_user(player_id).id

    DRAFTS[draft_id]['players'][player_name] = {
        'inbox': [],
        'packs': [[], [], [], [], [], [], [], []],
        'picks': {
            'corp': [],
            'runner': []
        },
        'has_open_pack': False
    }
    PLAYERS[player_name] = {
        'player_id': player_id,
        'draft_id': draft_id,
        'dm_id': player_dm_id
    }

    return 'ADD_SUCCESSFUL'


def remove_player(player_name, draft_id):
    if draft_id not in DRAFTS:
        return 'Draft `{draft_id}` does not exist.'.format(draft_id=draft_id)
    if DRAFTS[draft_id]['metadata']['has_started']:
        return 'Draft `{draft_id}` has already started.'.format(draft_id=draft_id)
    if player_name not in get_players(draft_id):
        return 'You were not registered for `{draft_id}`.'.format(draft_id=draft_id)
    del DRAFTS[draft_id]['players'][player_name]
    return 'ok'


def assign_seat_numbers(draft_id):
    num_players = get_num_players(draft_id)
    seats = list(range(num_players))
    random.shuffle(seats)
    for player in get_players(draft_id):
        PLAYERS[player]['seat_number'] = seats.pop(0)


# Draft Operations

async def open_new_pack(draft_id):
    """
    Sends first set of picks to players.
    After this the pack-sending logic is entirely event-driven.
    """
    for player in get_players(draft_id):
        pack = DRAFTS[draft_id]['players'][player]['packs'].pop(0)
        DRAFTS[draft_id]['players'][player]['inbox'].append(pack)

        for i, card in enumerate(pack):
            await send_card(player,card)

        DRAFTS[draft_id]['players'][player]['has_open_pack'] = True


def handle_pick(draft_id, player_name, card_code):
    pack = DRAFTS[draft_id]['players'][player_name]['inbox'].pop(0)
    for i, card in enumerate(pack):
        if card['code'] == card_code:
            card_index = i
            break
    picked_card = pack.pop(card_index)
    add_card_to_picks(draft_id, player_name, picked_card)
    DRAFTS[draft_id]['players'][player_name]['has_open_pack'] = False
    if len(pack) > 0:
        pass_pack(draft_id, player_name, pack)


def add_card_to_picks(draft_id, player_name, picked_card):
    draft = DRAFTS[draft_id]
    player = draft['players'][player_name]
    player_picks = player['picks'][picked_card['side_code']]
    player_picks.append(picked_card['title'])


def pass_pack(draft_id, player_name, pack):
    player_seat = get_seat_number(player_name)
    next_seat = (player_seat + 1) % get_num_players(draft_id)
    for player in get_players(draft_id):
        if get_seat_number(player) == next_seat:
            DRAFTS[draft_id]['players'][player]['inbox'].append(pack)


async def open_next_pack(draft_id, player):
    pack = DRAFTS[draft_id]['players'][player]['inbox'][0]
    
    await send_dm(
        player_id=get_player_dm_id(player),
        content='Here is your next pack.'
    )
    for card in pack:
        await send_card(player,card)
    
    DRAFTS[draft_id]['players'][player]['has_open_pack'] = True


async def open_next_pack_or_wait(draft_id, player_id, card):

    card_name = card['title']
    await send_dm(
        player_id=player_id, 
        content='{} was picked. A new pack will open once it is passed to you.'.format(card_name)
    )
    need_new_pack = True
    
    for player in get_players(draft_id):
        if player_has_pack_waiting(draft_id, player):
            need_new_pack = False
            if not player_has_open_pack(draft_id, player):
                await open_next_pack(draft_id, player)

    if need_new_pack:
        if draft_finished(draft_id):
            for player in get_players(draft_id):
                # SLACK METHOD - REPLACE WITH DISCORD RED METHOD
                await send_dm(
                    player_id=get_player_dm_id(player),
                    content='The draft is complete! Here are your picks:'
                )
                picks = get_picks(draft_id, player)
                
                await send_dm(
                    player_id=get_player_dm_id(player),
                    text=format_picks('Corp:\n\n', picks['corp'])
                )
                await send_dm(
                    player_id=get_player_dm_id(player),
                    text=format_picks('Runner:\n\n', picks['runner'])
                )
            cleanup(draft_id)
        else:
            await open_new_pack(draft_id)


def cleanup(draft_id):
    del DRAFTS[draft_id]
    # make a copy for iteration so you can delete from the real one
    for player in list(PLAYERS.keys()):
        if PLAYERS[player]['draft_id'] == draft_id:
            del PLAYERS[player]


def format_picks(heading, picks):
    picks_copy = picks[:]
    for i, card in enumerate(picks_copy):
        if i < 5 or 49 < i < 53:
            pre = '1 '
        else:
            pre = '3 '
        picks_copy[i] = pre + card
    cards = '\n'.join(picks_copy)
    return '```' + heading + '\n' + cards + '```'

# Endpoints / Slash Commands
@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!pick'):
        if len(message.content.split()) > 1:
            card_code = message.content.split()[1]
            draft_id = PLAYERS[message.author.name]['draft_id']
            handle_pick(draft_id, message.author.name, card_code)
            card = get_card(card_code)
            await open_next_pack_or_wait(draft_id, message.author.id,card)
        else:
            await send_dm(
                player_id = message.author.id,
                content = 'Missing card code!'
            )
        

    if message.content.startswith('!debug'):
        if message.author.name == await get_owner():
            with open('debug.log', 'w') as f:
                f.write(json.dumps({
                    'dumped_at': time.strftime("%Y-%m-%d %H:%M"),
                    'PLAYERS': PLAYERS,
                    'DRAFTS': DRAFTS
                }, indent=4, sort_keys=True))
            msg = 'Dump successful.'
        else:
            msg = 'Only an admin can use this command.'
            print('User {0.author.name} tried to debug instead of {owner}'.format(message,owner=OWNER))
        await send_dm(
            player_id = message.author.id,
            content = msg
        )

    if message.content.startswith('!createdraft'):
        user_name = message.author.name
        if user_can_create_draft(user_name):
            user_id = message.author.id
            new_draft_code = setup_draft(user_name, user_id)
            msg = '''Draft successfully created. Your draft ID is `{draft_id}`. 
            Other players can use this code with the `!joindraft {draft_id}` command 
            to join the draft.
            '''.format(draft_id=new_draft_code)
        else:
            msg = '''
            You can only create one draft at a time. You can use 
            `!canceldraft [draft_id]` to quit and then start over.
            '''
        await send_dm(
            player_id = message.author.id,
            content = msg
        )

    if message.content.startswith('!canceldraft'):
        if len(message.content.split()) > 1:
            user_name = message.author.name
            draft_id = message.content.split()[1]
            if user_name != get_creator(draft_id):
                msg = 'Only the draft creator can cancel it.'
            elif draft_id not in DRAFTS:
                msg = 'Draft does not exist.'
            elif draft_started(draft_id):
                msg = 'Draft `{draft_id}` has already started.'.format(draft_id=draft_id)
            else:
                await _cancel_draft(draft_id)
                msg = 'Draft successfully cancelled.'
        else:
            msg = 'Missing draft id!'
        await message.channel.send(msg)

    if message.content.startswith('!startdraft'):
        if len(message.content.split()) > 1:
            draft_id = message.content.split()[1]
            user_name = message.author.name
            if user_name != get_creator(draft_id):
                msg  = 'Only the draft creator can start the draft.'
            elif draft_id not in DRAFTS:
                msg = 'Draft does not exist.'
            elif draft_started(draft_id):
                msg = 'Draft `{draft_id}` has already started.'.format(draft_id=draft_id)
            else:
                await message.channel.send('Draft `{draft_id}` is starting!'.format(draft_id=draft_id))
                setup_packs(draft_id)
                assign_seat_numbers(draft_id)
                DRAFTS[draft_id]['metadata']['has_started'] = True
                for player in get_players(draft_id):
                    
                    await send_dm(
                        player_id=get_player_id(player),
                        content='Welcome to the draft! Here is your first pack. Good luck!'
                    )
                await open_new_pack(draft_id)
            
        else:
            await send_dm(
                player_id = message.author.id,
                content='Missing draft id!'
            )

    if message.content.startswith('!joindraft'):
        if len(message.content.split()) > 1:
            draft_id = message.content.split()[1]
            player_name = message.author.name
            player_id = message.author.id
            if draft_id not in DRAFTS:
                msg = 'Draft does not exist.'
            elif player_name in get_players(draft_id):
                msg = 'You can not join the same draft more than once.'
            elif draft_started(draft_id):
                msg = 'Draft `{draft_id}` has already started.'.format(draft_id=draft_id)
            else:
                add_player(player_name, player_id, draft_id)
                creator_name = get_creator(draft_id)
                creator_id = get_player_id(creator_name)
                num_players = get_num_players(draft_id)
                await send_dm(
                    player_id=creator_id,
                    content='''
                        {player} has joined your draft (`{draft}`). There are now
                        {num} players registered.
                    '''.format(player=player_name, draft=draft_id, num=num_players)
                )
                msg = '''
                    Successfully joined draft `{draft_id}`. Please wait for `{creator}`
                    to begin the draft.
                '''.format(draft_id=draft_id, creator=creator_name)
            await send_dm(
                player_id = message.author.id,
                content = msg
            )
        else:
            await send_dm(
                player_id = message.author.id,
                content='Missing draft id!'
            )

    if message.content.startswith('!leavedraft'):
        if len(message.content.split()) > 1:
            draft_id = message.content.split()[1]
            player_name = message.author.name
            # remove_player() does the checks I usually do here
            res = remove_player(player_name, draft_id)
            if res != 'ok':
                msg = 'Failed to leave draft. Error: ' + res
            elif player_name == get_creator(draft_id):
                _cancel_draft(draft_id)
                msg = '''
                    Successfully withdrew from draft `{draft_id}`. 
                    Because you were the creator of this draft it has 
                    been cancelled. The other players have been notified.
                '''.format(draft_id=draft_id)
            else:
                creator_name = get_creator(draft_id)
                creator_id = get_player_dm_id(creator_name)
                num_players = get_num_players(draft_id)
                await send_dm(
                    player_id = creator_id,
                    content = '''
                        {player} has left your draft (`{draft}`). There are now 
                        {num} players registered.
                        '''.format(player=player_name, draft=draft_id, num=num_players)
                )
                msg = 'Successfully withdrew from draft `{draft_id}`.'.format(draft_id=draft_id, creator=creator_name)

            await send_dm(
                player_id = message.author.id,
                content = msg
            )
        else:
            await send_dm(
                player_id = message.author.id,
                content='Missing draft id!'
            )


    if message.content.startswith('!showpicks'):
        player_name = message.author.name
        if player_name not in PLAYERS:
            await send_dm(
                player_id = get_player_dm_id(player_name),
                content = 'You are not enrolled in a draft.'
            )
        else:
            draft_id = PLAYERS[player_name]['draft_id']
            # SLACK METHOD - REPLACE WITH DISCORD RED METHOD
            await send_dm(
                player_id =get_player_dm_id(player_name),
                content='Here are your picks so far:'
            )
            picks = get_picks(draft_id, player_name)
            # SLACK METHOD - REPLACE WITH DISCORD RED METHOD
            await send_dm(
                player_id=get_player_dm_id(player_name),
                content=format_picks('Corp:\n\n', picks['corp'])
            )
            # SLACK METHOD - REPLACE WITH DISCORD RED METHOD
            await send_dm(
                player_id=get_player_dm_id(player_name),
                content=format_picks('Runner:\n\n', picks['runner'])
            )

@client.event
async def on_ready():
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
    appinfo = client.appinfo
    print('Application name and owner')
    print(appinfo.name)
    print(await get_owner())
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


async def _cancel_draft(draft_id):
    for player in get_players(draft_id):
        # SLACK METHOD - REPLACE WITH DISCORD RED METHOD
        await send_dm(
            player_id=get_player_dm_id(player),
            content='''
                Draft `{draft_id}` was cancelled by 
                `{creator}`.
                '''.format(
                    draft_id=draft_id,
                    creator=get_creator(draft_id)
                )
            
        )
    cleanup(draft_id)

async def get_owner():
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
    return client.appinfo.owner.name


if __name__ == '__main__':
    client.run(TOKEN)
