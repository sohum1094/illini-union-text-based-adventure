from aiohttp import web
from aiohttp.web import Request, Response, json_response
import random

routes = web.RouteTableDef()

hub_server_url = None
domain_id = None
domain_secret = None

domain_state = {
    'rooms': {
        'lobby': {
            'description': "You're in the lobby of the Union, unless it is a waiting room? There are a chairs and tables all around the room. You see a help desk to the east and a few fish swimming in a fish tank in the middle of the room. To the west is a pair of double doors leading to a hallway of some kind. To the south is multiple leading to what looks like a courtyard. You can exit to the north.",
            'visited': False,
            'west': 'hallway',
            'north': 'exit',
            'south': 'courtyard',
        },
        'hallway': {
            'description': "You're in a long hallway with many windows and doors. To the North, you see a lobby with many chairs and tables. To the South you see an ornate lounge with a lot of sunshine. To the West, you see a closet and many exit doors blocked off for construction. Lastly, in the east you double doors leading you to a courtyard.",
            'visited': False,
            'east': 'courtyard',
            'north': 'lobby',
            'south': 'lounge',
            'west': 'closet'
        },
        'courtyard': {
            'description': "You're in the courtyard, you see many chairs and tables, some people are studying, others gossiping, most of them scrolling on instagram trying to 'lock in'. You get a whiff of coffe from the Starbucks to the east. You look to the west and see a hallway with exit doors. The Union lobby is through the double doors on the north side. You also see stage with a microphone in the room, you suddenly find the urge to sing.",
            'visited': False,
            'north': 'lobby',
            'west': 'hallway',
            'east': 'starbucks',
        },
        'starbucks': {
            'description': "You follow the smell of coffee into the Starbucks. You read the menu and see students have ordered so many drinks during finals week, the only drink left is a peppermint mocha. Should you order a drink? The courtyard is to the west.",
            'visited': False,
            'west': 'courtyard',
        },
        'lounge': {
            'description': "The sunshine draws you into the lounge. The antique decor and beautiful view of the quad are serene. You see a piano in the corner of the room, and feel an urge to play the piano. You see the hallway to the west.",
            'visited': False,
            'west': 'hallway',
        },
        'closet': {
            'description': "You're in a closet with brooms and dustpans around. You look up and see a music note on a note-sheet peeking over the edge of the shelf. You can exit the closet east to the hallway.",
            'visited': False,
            'east': 'hallway',
        }
    },
    'items': [],
    # contains everything about user state including furniture state as well as user inventory, etc.
    'users': {},
}

@routes.post('/newhub')
async def register_with_hub_server(req: Request) -> Response:
    """Used by web UI to connect this domain to a hub server.
    
    1. web calls domain's /register, with hub server URL payload
    2. domain calls hub server's /register, with name, description, and items
    3. hub server replies with domain's id, secret, and item identifiers
    """
    # partially implemented for you:
    url = await req.text()
    
    global hub_server_url, domain_secret, domain_id
    hub_server_url = url
    
    domain_items = [
        {
            "name": "i-card",
            "description":"A UIUC admin's i-card,\nI wonder what this could open...",
            "verb": {
            },
            "location": "lobby",
        },
        {
            "name": "sheet-music",
            "description":"A very old crinkly sheet of music with 'Bohemian Rhapsody' written on it. Hmm, the admin must've been a Queen fan",
            "verb": {
                # look/read music
                # play music
            },
            "location": "closet",
        },
        {
            "name": "drink-voucher",
            "description":"A very olf starbucks drink voucher. 'This vocuher entitles you to one free drink of your choice'",
            "verb": {
                # use voucher
            },
            "location": "lounge",
        },
        {
            "name": "peppermint-mocha",
            "description":"A nice and steamy holiday drink. I can't wait to taste it.",
            "verb": {
                # drink
            },
            "location": "starbucks",
        },
        {
            "name": "piano-key",
            "description":"A black piano key... without the rest of the piano. That's odd.",
            "verb": {},
            "depth": 1,
        },
        {
            "name": "rubber-gloves",
            "description":"Arm length, bright-yellow, waterproof gloves.",
            "verb": {},
            "depth": 0,
        },
    ]
    
    async with req.app.client.post(url+'/register', json={
          'url': whoami,
          'name': "Sohum's Illini Union",
          'description': "A snapshot of the UIUC Union and its many rooms.",
          'items': domain_items,
      }) as resp:
          data = await resp.json()
          if 'error' in data:
              return json_response(status=resp.status, data=data)
    
    try:
        # TO DO: store the url and the values in the returned data for later use
        domain_id, domain_secret = data['id'], data['secret']
        # TO DO: clear any user/game state to its initial state
        domain_state['users'].clear()
        
        for i, item in enumerate(domain_items):
                item_id = data['items'][i]
                # Store in the domain_state dictionary, not domain_items
                item['id'] = item_id
                domain_state['items'].append(item) 
    except Exception as e:
        return json_response(data = {'error': f'Error during /newhub: {e}'}, status = 500)
    return json_response(data={'ok': 'woah registration is working'}, status=200)


@routes.post('/arrive')
async def handle_arrive(req: Request) -> Response:
    """Called by hub server each time a user enters or re-enters this domain."""
    data = await req.json()
    user_id = data['user']
    incoming_dir = data['from']
    global domain_secret
    if data['secret'] != domain_secret:
            return json_response(data = {'error': 'secrets do not match'}, status=  400)
    
    if user_id not in domain_state['users'] or incoming_dir == 'login':
        initialize_user(user_id)
    else:
        if incoming_dir == 'west':
            domain_state['users'][user_id]['location'] = 'hallway'
        elif incoming_dir == 'east':
            domain_state['users'][user_id]['location'] = 'courtyard'
        elif incoming_dir in ['south', 'direct']:
            domain_state['users'][user_id]['location'] = 'lobby'
        elif incoming_dir == 'north':
            domain_state['users'][user_id]['location'] = 'lounge'
        
    
    # owned items (from this domain)
    domain_state['users'][user_id]['owned'] = data['owned']
    # carried items (from other domains)
    domain_state['users'][user_id]['carried'] = data['carried']
    # dropped items (these are items user left in this domain, with location info)
    domain_state['users'][user_id]['dropped'] = data['dropped']
    # prize items
    domain_state['users'][user_id]['prize'] = data['prize']

    return json_response(status=200)

@routes.post('/depart')
async def handle_depart(req: Request) -> Response:
    """Called by hub server each time a user leaves this domain."""
    data = await req.json()
    user_id = data['user']
    
    domain_state['users'][user_id]['location'] = 'away'
    
    return json_response(status=200)
    
    


@routes.post('/dropped')
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user drops an item in this domain.
    The return value must be JSON, and will be given as the location on subsequent /arrive calls
    """
    data = await req.json()
    user_id = data['user']
    item_data = data['item']  # This is now a dictionary, e.g. {"name": "paper", ...}

    global domain_secret
    if data['secret'] != domain_secret:
        return json_response(data={'error': 'secrets do not match'}, status=400)

    user_loc = domain_state['users'][user_id]['location']

    item_id = item_data['id']
    # Check that the item is known globally
    
    if item_id not in [it['id'] for it in domain_state['items']]:
        return json_response(data={'error': 'Item not recognized'}, status=400)

    for item in domain_state['users'][user_id]["carried"]:
        if item['id'] == item_id:
            # print('dropping item {} in {}'.format(item['id'], user_loc))
            item['location'] = user_loc
            domain_state['users'][user_id]["dropped"].append(item)
            domain_state['users'][user_id]["carried"].remove(item)
    for item in domain_state['users'][user_id]["owned"]:
        if item['id'] == item_id:
            # print('dropping item {} in {}'.format(item['id'], user_loc))
            item['location'] = user_loc
            domain_state['users'][user_id]['items'].append(item)
            domain_state['users'][user_id]["owned"].remove(item)

    return json_response(data=user_loc)


@routes.post("/command")
async def handle_command(req : Request) -> Response:
    """Handle hub-server commands"""    
    data = await req.json()
    user_id = data['user']
    command = data['command']
    
    if user_id in domain_state['users'] and domain_state['users'][user_id]['location'] == 'away':
        return Response(text = "User is away, cannot send commands until next /arrive.", status= 409)
    
    if user_id not in domain_state['users']:
        return Response(text="You have to journey to this domain before you can send it commands.")
        
    if command == ['look', 'fishtank'] or command == ['look', 'fish', 'tank']:
        if domain_state['users'][user_id]['location'] == 'lobby':
            if domain_state['users'][user_id]['dynamic state']['fish tank'] == 'with card':
                output = "You see a few fish swimming around, one seems to be bumping into something sticking out of the sand and rocks at the bottom. I wonder what that is. Maybe you should go fishing."
            elif domain_state['users'][user_id]['dynamic state']['fish tank'] == 'card discovered':
                output = "You see a few fish swimming around. There is an i-card at the bottom, try taking it."
            elif domain_state['users'][user_id]['dynamic state']['fish tank'] == 'card taken':
                output = "You see a few fish swimming around. You already took the i-card."
            return Response(text = output)
        
    elif command == ['go','fishing']:
        if domain_state['users'][user_id]['location'] == 'lobby':
            if has_local_item_in_inventory('rubber-gloves', user_id):
                if domain_state['users'][user_id]['dynamic state']['fish tank'] == 'with card':
                    output = "You feel a plastic card sitting at the bottom, maybe it is an i-card."
                    domain_state['users'][user_id]['dynamic state']['fish tank'] = 'card discovered'
                elif domain_state['users'][user_id]['dynamic state']['fish tank'] == 'card discovered':
                    output = "You feel a plastic card sitting at the bottom. Try taking the i-card."
                    domain_state['users'][user_id]['dynamic state']['fish tank'] = 'card taken'
                elif domain_state['users'][user_id]['dynamic state']['fish tank'] == 'card taken':
                    output = "You already took the i-card"
            else:
                output = "Those fish look like the might bite you, maybe you should use some wear some gloves."
            return Response(text = output)
    
    elif command == ['use', 'i-card', 'closet']:
        if domain_state['users'][user_id]['location'] == 'hallway':
            if has_local_item_in_inventory('i-card', user_id):
                output = "You swipe the i-card and unlock the door to the closet"
                domain_state['users'][user_id]['dynamic state']['closet door'] = 'unlocked'
            else:
                output = "You don't have an i-card, the closet remains locked."
            return Response(text = output)
                
    elif command == ['go', 'west'] and domain_state['users'][user_id]['location'] == 'hallway':
        if domain_state['users'][user_id]['dynamic state']['closet door'] == 'locked':
            output = "The door is locked. There seems to be an i-card scanner on the door."
        elif domain_state['users'][user_id]['dynamic state']['closet door'] == 'unlocked':
            domain_state['users'][user_id]['location'] = 'closet'
            output = room_info(domain_state['users'][user_id]['location'], user_id)
        return Response(text = output)
    
    elif command == ['go', 'east'] and domain_state['users'][user_id]['location'] == 'lobby':
        output = "You speak with the staff at the help desk, they mention they got some new fish in the tank that you should take a look at. (Try to 'look fishtank') You return back to the lobby"
        return Response(text = output)
    
    elif command == ['play', 'piano'] and domain_state['users'][user_id]['location'] == 'lounge':
        if not has_local_item_in_inventory('sheet-music', user_id):
            output = "You sit down, and you think of what to play... you realize you don't know any songs. You get up."
        else:
            if domain_state['users'][user_id]['dynamic state']['piano'] == 'missing key':
                output = "You sit down, place your fingers to play, ding, ding, OW... it seems there is a missing key in the piano. Try using a piano key on the piano."
            elif domain_state['users'][user_id]['dynamic state']['piano'] == 'fixed':
                output = "You begin to play Bohemian Rhapsody, wow you are actually doing it. Ding, ding, thunk... that doesn't sound right. Seems like there might be something wrong inside the piano. Try opening it up."
            
        return Response(text = output)
    
    elif command == ['use', 'piano-key', 'piano'] and domain_state['users'][user_id]['location'] == 'lounge':
        if domain_state['users'][user_id]['dynamic state']['piano'] == 'missing key':
            if has_local_item_in_inventory('piano-key', user_id):
                output = 'You place the piano key into the piano, now it looks ready to play'
                domain_state['users'][user_id]['dynamic state']['piano'] = 'fixed'
            else:
                output = 'You do not have a piano key to fix this. Maybe its somewhere else.'
    
    elif (command == ['look', 'piano'] or command == ['open', 'piano']) and domain_state['users'][user_id]['location'] == 'lounge':
        if domain_state['users'][user_id]['dynamic state']['piano'] == 'fixed':
            domain_state['users'][user_id]['dynamic state']['piano'] == 'open'
            output = "You open the piano and see something inside... A voucher of some sort."
        elif domain_state['users'][user_id]['dynamic state']['piano'] == 'missing key':
            output = "You try to open the piano think maybe you should try playing it first before you break anything."
        elif domain_state['users'][user_id]['dynamic state']['piano'] == 'open':
            output = "The piano is already opedn, you see a voucher inside. Try to take the voucher."
        return Response(text = output)
    
    elif (command == ['give', 'voucher'] or command == ['use','voucher','starbucks']) and domain_state['users'][user_id]['location'] == 'starbucks':
        if has_local_item_in_inventory('voucher', user_id):
            if domain_state['users'][user_id]['dynamic state']['starbucks'] == 'has drink':
                output = "You give the voucher to the barista, they look confused for a second, but then get to work. For some reason they getup on a ladder and pull something from the ceiling tile while making your drink. Hmm, odd. After a few minutes, the barista places a steamy peppermint-mocha on the table. Yay!"
                domain_state['users'][user_id]['dynamic state']['starbucks'] == 'drink served'
                for i in range(len(domain_state['users'][user_id]['owned'])):
                    if domain_state['users'][user_id]['owned'][i]['name'] == 'voucher':
                        del domain_state['users'][user_id]['owned'][i]
        elif domain_state['users'][user_id]['dynamic state']['starbucks'] == 'has drink':
            output = "Hmm the peppermint-mocha does look good, but you don't have any money, maybe theres something else that can help you get a drink."
        elif domain_state['users'][user_id]['dynamic state']['starbucks'] == 'drink served':
            output = "Your drink has been served, pickup your steamy peppermint-mocha before it get cold."
            domain_state['users'][user_id]['dynamic state']['starbucks'] == 'drink taken'
        elif domain_state['users'][user_id]['dynamic state']['starbucks'] == 'drink taken':
            output = "You have already taken the peppermint-mocha, try to drink it."
        
        return Response(text = output)
    
    elif command == ['drink', 'starbucks'] or command == ['drink', 'peppermint-mocha']:
        if has_local_item_in_inventory('peppermint-mocha', user_id):
            output = "It smells so good... *sip*... yum- EW. Something doesn't taste right about this. *you open the coffe cup and see something floting inside* WHAT IS THIS. *you immediately drop your drink, spilling the mocha and the foreign object on the ground."
            domain_state['users'][user_id]['dynamic state']['drink'] = "investigated"
            domain_state['users'][user_id]['dynamic state']['drink spill location'] = domain_state['users'][user_id]['location']
        else:
            output = "You have not picked up the drink yet."
        
        return Response(text = output)
    
    elif command == ['go', 'south'] and domain_state['users'][user_id]['location'] == 'courtyard':
        output = "You bravely step on the stage. After a few moments you begin to a panic a little. You start to sing 'Dancing Queen'... *screech* your voice cracks and you rush back into the courtyard, people staring at you."
        return Response(text = output)
        
    elif command[0] == "look":
        if len(command) > 1:
            for item in domain_state['users'][user_id]['owned']:
                if command[1] == item['name'] or command[1] == item['id'] :
                    output = item['description']
                    return Response(text = output)
            for item in domain_state['users'][user_id]['carried']:
                if command[1] == item['name'] or command[1] == item['id'] :
                    output = item['description']
                    return Response(text = output)
            return Response(text = "I don't know how to do that.")
        else:
            output = room_info(domain_state['users'][user_id]['location'], user_id)
            return Response(text = output)
        
    elif command[0] == "take":
        #from room 
        for source, destination in [('items','owned'),('dropped', 'carried'),('prize','carried')]:
            # print('using source {} and destintion {} to move {}'.format(source, destination, command[1]))
            
            for item in domain_state['users'][user_id][source]:
                if item['name'] == command[1] or item['id'] == command[1]:
                    if item.get('depth', -1) == 2 and source == 'prize' and domain_state['users']['dynamic state']['drink spilled location'] == 'not spilled':
                        break
                    item['location'] = 'inventory'
                    domain_state['users'][user_id][destination].append(item)
                    domain_state['users'][user_id][source].remove(item)
                    async with req.app.client.post(hub_server_url+'/transfer', json={ 
                        "domain": domain_id # your domain's ID as given during /newhub
                        ,"secret": domain_secret # your domain's secret as given during /newhub
                        ,"user": user_id   # the user ID as given in /arrive
                        ,"item": item['id']   # a numerical item ID
                        ,"to": 'inventory'     # where you want the item to go
                    }) as resp:
                        data = await resp.json()
                        if 'error' in data:
                            return json_response(status=resp.status, data=data)
                    if item.get('depth', -1) == 2:
                        async with req.app.client.post(hub_server_url+'/score', json={ 
                            "domain": domain_id # your domain's ID as given during /newhub
                            ,"secret": domain_secret # your domain's secret as given during /newhub
                            ,"user": user_id   # the user ID as given in /arrive
                            ,"score": 1.0     # where you want the item to go
                        }) as resp:
                            data = await resp.json()
                            if 'error' in data:
                                return json_response(status=resp.status, data=data)
                        return Response(text = "You have taken the {}. You have finished this domain, congrats!".format(command[1]))
                    return Response(text = "You have taken the {}".format(command[1]))

                
        return Response(text = "There's no {} here to take".format(command[1]))
    
    elif command[0] == "drop":
        
        # print('checking user inventory to drop {}: {}'.format(command[1],domain_state['users'][user_id]["carried"]))
        for destination, source in [('items','owned'),('dropped', 'carried')]:
            for item in domain_state['users'][user_id][source]:
                if item['name'] == command[1]:
                    # print('dropping item {} in {}'.format(item['name'], domain_state['users'][user_id]['location']))
                    item['location'] = domain_state['users'][user_id]['location']
                    domain_state['users'][user_id][destination].append(item)
                    domain_state['users'][user_id][source].remove(item)
                    # print('after command drop owned: {} \nitems: {}'.format(domain_state['users'][user_id]['owned'],domain_state['users'][user_id]['items']))

                    return Response(text = domain_state['users'][user_id]['location'])
    elif command[0] == "go":
        
        direction = command[1]
        if direction in domain_state['rooms'][domain_state['users'][user_id]['location']].keys():
            destination = domain_state['rooms'][domain_state['users'][user_id]['location']][direction]
            if destination == 'exit':
                return Response(text = "$journey east")
            domain_state['users'][user_id]['location'] = destination
            output = room_info(domain_state['users'][user_id]['location'], user_id)
            return Response(text = output)
        return Response(text = "You can't go that way from here.")
    

            
    else:
        action_item = command[1] if len(command) > 1 else None
        action_verb = command[0]
        print('carried items: {}'.format(domain_state['users'][user_id]['carried']))
        print('owned items: {}'.format(domain_state['users'][user_id]['owned']))
        for lst in ["carried", "owned"]:
            for item in domain_state['users'][user_id][lst]:
                if action_item == item['name'] or action_item == item['id']:
                    if action_verb in item['verb']:
                        output = item['verb'][action_verb]
                        if output:
                            return Response(text = output)
    return Response(text = "I don't know how to do that.")


def initialize_user(user_id):
    # Each user gets their own session of items, furniture, etc.
    # This ensures one user's actions don't affect another.
    domain_state['users'][user_id] = {
        'location': 'lobby',
        'dynamic state': {
            'fish tank': 'with card',
            'piano': 'missing key',
            'closet door': 'locked',
            'starbucks': 'has drink',
            'drink': 'undiscovered',
            'drink spill location': 'not spilled',
        },
        'items': [],
        'owned': [],
        'carried': [],
        'dropped': [],
        'prize': [],
    }
    for item in domain_state['items']:
        domain_state['users'][user_id]['items'].append(item)

def room_info(location, user_id):
    output = domain_state['rooms'][location]['description']
    
    room_items = items_in_room(location, user_id)
    for item in room_items:
        output += '\nThere is a {} <sub>{}</sub> here.'.format(item["name"], item['id'])
    
    return output

def items_in_room(location, user_id):
    """Return a list of items present in the given location."""
    output = []
    for item in domain_state['users'][user_id]['items']:
        if item.get('location', None) == location:
            if item['name'] == 'i-card' and domain_state['users'][user_id]['dynamic state']['fish tank'] in ['with card', 'card taken']:
                print('i-card not discovered yet')
            elif item['name'] == 'drink-voucher' and domain_state['users'][user_id]['dynamic state']['piano'] in ['fixed', 'missing key']:
                print('voucher not discovered yet')
            else:
                output.append(item)
            
    
    # print('items in room, prize list: {}'.format(domain_state['users'][user_id]['prize']))
    if domain_state['users'][user_id]['location'] == domain_state['users'][user_id]['dynamic state']['drink spill location']:
        for item in domain_state['users'][user_id]['prize']:
            if item.get('depth', -1) == 2:
                output.append(item)
    if domain_state['users'][user_id]['location'] == 'closet':
        for item in domain_state['users'][user_id]['prize']:
            if item.get('depth', -1) == 1:
                output.append(item)
    if domain_state['users'][user_id]['location'] == 'hallway':
        for item in domain_state['users'][user_id]['prize']:
            if item.get('depth', -1) == 0:
                output.append(item)
    return output

def has_local_item_in_inventory(item_name, user_id):
    # print('looking for {} in inventory'.format(item_name))
    # print('locally owned items are {}'.format(domain_state['users'][user_id]['owned']))
    item_id = [it['id'] for it in domain_state['items'] if it['name'] == item_name]
    for it in domain_state['users'][user_id]['owned']:
        if it['id'] in item_id:
            print('found it')
            return True
    # print('didnt find it')
    return False















# Do not modify code below this line

@web.middleware
async def allow_cors(req, handler):
    """Bypass cross-origin resource sharing protections,
    allowing anyone to send messages from anywhere.
    Generally unsafe, but for this class project it should be OK."""
    resp = await handler(req)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

async def start_session(app):
    """To be run on startup of each event loop. Makes singleton ClientSession"""
    from aiohttp import ClientSession, ClientTimeout
    app.client = ClientSession(timeout=ClientTimeout(total=3))

async def end_session(app):
    """To be run on shutdown of each event loop. Closes the singleton ClientSession"""
    await app.client.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default="0.0.0.0")
    parser.add_argument('-p','--port', type=int, default=3400)
    args = parser.parse_args()

    import socket
    whoami = socket.getfqdn()
    if '.' not in whoami: whoami = 'localhost'
    whoami += ':'+str(args.port)
    whoami = 'http://' + whoami
    print("URL to type into web prompt:\n\t"+whoami)
    print()

    app = web.Application(middlewares=[allow_cors])
    app.on_startup.append(start_session)
    app.on_shutdown.append(end_session)
    app.add_routes(routes)
    web.run_app(app, host=args.host, port=args.port)
