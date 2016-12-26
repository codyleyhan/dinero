from flask import Blueprint, request, g, redirect, url_for, jsonify
from datetime import datetime, timedelta
import pprint

from app import db
from app.item.models.Item import Item
from app.auth.models.User import User
from app.item.validators.ItemValidator import ItemValidator
#from app.auth.decorators import requires_login, requres_status_manager



itemMod = Blueprint('item', __name__, url_prefix='/item')

##index
@itemMod.route('/', methods=['GET', 'POST'])
def index():
    #index page
    if request.method == 'GET':
        # Query all items in the database and return.
        items = get('all_items')
        return jsonify({
            'status': 'success',
            'data': [str(item) for item in items]
        }), 200

    # add item to database
    if request.method == 'POST':
        print("got into add_item()")
        # validate the inputted information.
        form = ItemValidator(data=request.json)
        if form.validate():
            # Check whether item exists
            name = request.json['name']
            check_item = get(name)
            if check_item:
                return jsonify({
                    'status': 'error',
                    'message': '%r already exists in your system.' % name,
                    'data': {
                        'item in database': serialize(check_item)
                    }
                }), 400

            #add item to database
            try:
                item = Item(request.json['name'], request.json['cost'], request.json['description'])
                db.session.add(item)
                db.session.commit()
                return jsonify({
                    'status': 'success',
                    'message': 'item added successfully.',
                    'data': {
                        'added item': item.serialize()
                    }
                }), 201
            except:
                return jsonify({
                    'status': 'error',
                    'message': 'there was an error adding the item',
                    'error': {
                        'key': ['errors here']
                    }
                }), 400
        return jsonify({
            'status': 'error',
            'message': 'there was an error with form validation',
            'error': form.errors
        }), 400

@itemMod.route('/<int:itemId>', methods=['GET', 'PUT', 'DELETE'])
def update(itemId):
    # retrieve and verify the existence of the Item from the database
    item = get(itemId)
    print(item)
    if not item:
        return jsonify({
            'status': 'error',
            'message': 'item %d not found in database.' % itemId
        }), 400

    # view a single Item
    if request.method == 'GET':
        item = serialize(item)
        return jsonify({
            'status': 'success',
            'message': 'found item successfully',
            'data': {
                'item': item
            }
        }), 200

    # update a single Item
    if request.method == 'PUT':
        form = ItemValidator(data=request.json)
        if form.validate():
            # cVerify that the update is indeed an update and not a duplication
            # of an item already in the database. If the item item being updated
            # in the database is indeed an attempt to duplicate, reroute user to
            # update form, displying current item at the top of the page.
            name = request.json['name']
            cost = request.json['cost']
            description = request.json['description']

            found_items = items_with_same(itemId, name, description)
            print(found_items)
            if not found_items:
                try:
                    item.name = name
                    item.cost = cost
                    item.description = description
                    db.session.commit()
                    item = serialize(item)

                    return jsonify({
                        'status': 'success',
                        'message': 'updated item',
                        'data': item
                    }), 200
                except:
                    return jsonify({
                        'status': 'error',
                        'message': 'error occured when updating item',
                        'error': {
                            'key': ['errors']
                        }
                    }), 400
            else:
                # unpack tuple `found_items` and get lengths of sub_tuples
                same_name, same_description = found_items
                num_same_name = len(same_name)
                num_same_description = len(same_description)

                #message to be returned to the user
                message = ""

                if num_same_name:
                    if num_same_name > 1:
                        message = '%d items with the same name exists.' % num_same_name
                        print("num_same_name > 1")
                    message = '1 item with the same name exist'
                    print("else num_same_name == 0")

                if num_same_description:
                    if num_same_description > 1 and num_same_name:
                        message += 'and %d items with the same description esists' % num_same_description
                    elif num_same_description > 1:
                        message += '%d items with the same description exists' % num_same_description
                    else:
                        message = '1 item with the same description exists'

                return jsonify({
                    'status': 'error',
                    'message': message,
                    'data': {
                        'items with same': {
                            'name': found_item_serialize(same_name),
                            'description': found_item_serialize(same_description)
                        }
                    }
                })
        return jsonify({
            'status': 'error',
            'message': 'there was an error with form validation',
            'error': form.errors
        }), 400

    # delete a single item
    if request.method == 'DELETE':
        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': '%d deleted from the database.' % itemId,
            }), 200
        except:
            return jsonify({
                'status': 'error',
                'message': '%r not deleted.',
                'errors': {
                    'key': ['errors here']
                }
            }), 400

## helper functions
# Query itemId and return the item to the caller.
# if an item with `itemId` is not found in the database, return False
def get(arg):
    if arg == 'all_items':
        item = Item.query.all()
        #print(item)
    elif type(arg) is str:
        item = Item.query.filter_by(name=arg).first()
    elif type(arg) is int:
        item = Item.query.filter_by(id=arg).first()
    if not item:
        return False
    return item

# Serialize the information passed in as item.
def serialize(item):
    return item.to_dict()

def items_with_same(id, name, description):
    print("enter items_with_same()")
    count = 0 # var to keep track of how many similar items there are

    same_name_item_list = Item.query.filter_by(name=name).all()
    same_name_dict = {} # empty dictionary to add any item that might be duplicates
    for item in same_name_item_list:
        if not item.id == id:
            count += 1
            print("snItem %d" % count)
            same_name_dict[count] = serialize(item)

    same_description_item_list = Item.query.filter_by(description=description).all()
    same_description_dict = {}
    for item in same_description_item_list:
        if not item.id == id:
            count += 1
            same_description[count] = serialize(item)
    #return both lists to the caller.
    return same_name, same_description

def found_item_serialize(found_items):
    list_of_items = []
    for key, value in found_items.items():
        #value = serialize(value)
        list_of_items.append({
            'found item #' : key,
            'id': value['id'],
            'name': value['name'],
            'cost': value['cost'],
            'description': value['description']
        })
    return list_of_items
