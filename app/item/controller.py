from flask import Blueprint, request, g, redirect, url_for, jsonify
#from datetime import datetime, timedelta

from app import db
from app.item.models.Item import Item
from app.auth.models.User import User
from app.item.validators.ItemValidator import ItemValidator

from app.auth import constants as USER
from app.auth.decorators import requires_login

from app.item.testFuncs import addTestItems

itemMod = Blueprint('item', __name__, url_prefix='/item')
dbs = db.session

#TODO Create Documentation

##index
@itemMod.route('/', methods=['GET', 'POST'], defaults={'path': ''})
@itemMod.route('/<path:path>', methods=['POST'])
@requires_login
def index(path):
    # authorized status based on login informatoin
    authorizedUser = g.user.role >= USER.MANAGER

    #index page
    if request.method == 'GET':
        page = None
        # check if user supplied a page number in query
        if request.args.get('page', ''):
            page = request.args.get('page', '')

            # check if page is a number
            try:
                page = int(page)
            except ValueError:
                page = 1

            if page < 0:
                page = 1
        else:
            page = 1

        # Query all items in the database and return.
        if authorizedUser:
            items = get('all_items')

            if items:
                return jsonify({
                    'status': 'success',
                    # Return allavailable information about all items
                    'data': [serialize(item) for item in items]
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'no items found'
                })

        else:
            items = get('all_items')
            return jsonify({
                'status': 'success',
                #return only `menu style` information
                'data': [serialize(item) for item in items]
            }), 200

    # add item to database
    if request.method == 'POST':
        if authorizedUser:
            if path == 'test':
                addTestItems()
                items = get('all_items')

                return jsonify({
                    'status': 'success',
                    'data': [serialize(item) for item in items]
                }), 200

            elif not path:
                # validate the inputted information.
                form = ItemValidator(data=request.json)
                if form.validate():

                    name = request.json['name']
                    cost = request.json['cost']
                    description = request.json['description']
                    category = request.json['category']

                    # Check whether item exists
                    found_items = items_with_same(name, description, cost)#, itemId)
                    if not any(found_items):
                        #add item to database
                        try:
                            item = Item(request.json['name'], request.json['cost'], request.json['description'], request.json['category'])
                            dbs.add(item)
                            dbs.commit()

                            return jsonify({
                                'status': 'success',
                                'message': 'item added successfully.',
                                'data': {
                                    'added item': serialize(item)
                                }
                            }), 201
                        except:
                            dbs.rollback()
                            return jsonify({
                                'status': 'error',
                                'message': 'there was an error adding the item',
                                'error': {
                                    'key': ['errors here']
                                }
                            }), 400

                    # Items exist. Let user know
                    else:
                        message, duplicate_item, dup_named_itmes, same_descriptioned_items = construct_return_package(found_items)

                        return jsonify({
                            'status': 'error',
                            'message': message,
                            'data': {
                                'duplicate items': serialize_found(duplicate_item),
                                'items with same': {
                                    'name': serialize_found(dup_named_itmes),
                                    'description': serialize_found(same_descriptioned_items)
                                }
                            }
                        }), 400

                    return jsonify({
                        'status': 'error',
                        'message': 'there was an error with form validation',
                        'error': form.errors
                    }), 400

                    # Was not able to process request
                #There was a problem with validating the form
                return jsonify({
                    'status': 'error',
                    'message': 'there was an error with form validation',
                    'error': form.errors
                }), 400

            # page not found
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'page not found.',
                    'error': 'route(%r) not found.' % path
                })
        #not authorized
        else:
            return jsonify({
                'status': 'error',
                'message': 'You are not authorized to update items.',
                'error': 'Forbidden Access'
            })

@itemMod.route('/<int:itemId>', methods=['GET', 'PUT', 'DELETE'])
@itemMod.route('/delete-all', defaults={'itemId': 0}, methods=['DELETE'])
def update(itemId):
    # authorized status based on login informatoin
    authorizedUser = g.user.role >= USER.MANAGER

    # verify the existence of and retrieve the Item from the database
    if itemId:
        item = get(itemId)
        if not item:
            return jsonify({
                'status': 'error',
                'message': 'item %d not found in database.' % itemId
            }), 400

    # view a single Item
        if request.method == 'GET':
            if not authorizedUser:
                item = serialize(item)
                return jsonify({
                    'status': 'success',
                    'message': 'found item successfully',
                    'data': {
                        'item': item
                    }
                }), 200
            else:
                # Return the raw form of the item
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
        if authorizedUser:
            form = ItemValidator(data=request.json)
            if form.validate():
                name = request.json['name']
                cost = request.json['cost']
                description = request.json['description']

                found_items = items_with_same(name, description, cost, itemId)

                # If no items were found in the database containing the same
                # description and/or name, then update the item accordingly.
                # Otherwise, keep the Item intact as is, i.e. do not modify Item
                if not any(found_items):
                    try:
                        item.name = name
                        item.cost = cost
                        item.description = description
                        dbs.commit()
                        item = serialize(item)

                        return jsonify({
                            'status': 'success',
                            'message': 'updated item',
                            'data': item
                        }), 200
                    except:
                        # Something went wrong in updating the item and the database
                        # has been rolledback to the state immediately before
                        # attempting to update
                        dbs.rollback()
                        return jsonify({
                            'status': 'error',
                            'message': 'error occured when updating item. Database hase been rolled back.',
                            'error': {
                                'key': ['errors']
                            }
                        }), 400
                else:
                    # Some form of duplication, wether it be name, description, category, id, etc.,
                    # Detected, and no update will occur
                    message, duplicate_item, dup_named_itmes, same_descriptioned_items = construct_return_package(found_items)

                    return jsonify({
                        'status': 'error',
                        'message': message,
                        'data': {
                            'duplicate items': serialize_found(duplicate_item),
                            'items with same': {
                                'name': serialize_found(dup_named_itmes),
                                'description': serialize_found(same_descriptioned_items)
                            }
                        }
                    }), 400
            # The form was not validated.
            return jsonify({
                'status': 'error',
                'message': 'there was an error with form validation',
                'error': form.errors
            }), 400
        # Whoever is trying to update is not authorized to do so.
        else:
            return jsonify({
                'status': 'error',
                'message': 'You are not authorized to update information',
                'error': 'Forbidden Access'
            })

    # delete a single item
    if request.method == 'DELETE':
        if authorizedUser:
            if request.path == '/item/delete-all':
                try:
                    numDeleted = Item.query.delete()
                    dbs.commit()
                    return jsonify({
                        'status': 'success',
                        'message': '%d item(s) successfully removed from the data base.' % numDeleted,
                    }), 202
                except:
                    dbs.rollback()
                    return jsonify({
                        'status': 'error',
                        'message': 'there was an error deleting all items from the data base'
                    }), 500
            elif itemId:
                # Delete a single item
                try:
                    dbs.delete(item)
                    dbs.commit()
                    return jsonify({
                        'status': 'success',
                        'message': '%d deleted from the database.' % itemId,
                    }), 200
                except:
                    # Error while deleteing or commiting a delete to dbs;
                    # rollback the database.
                    dbs.rollback()
                    return jsonify({
                        'status': 'error',
                        'message': '%r not deleted.',
                        'errors': {
                            'key': ['errors here']
                        }
                    }), 400
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'error. second to last else in update()'
                })
        else:
            #user is not authorized to delete.
            return jsonify({
                'status': 'error',
                'message': 'You are not authorized to update information',
                'error': 'Forbidden Access'
            })

## helper functions
# Query itemId and return the item to the caller.
# if an item with `itemId` is not found in the database, return False
def get(arg):
    if arg == 'all_items':
        item = Item.query.all()
    if arg == 'all_items':
        item = Item.query.all()
    elif type(arg) is str:
        item = Item.query.filter_by(name=arg).first()
    elif type(arg) is int:
        item = Item.query.filter_by(id=arg).first()
    if not item:
        return False
    return item

# Wrapper for .to_dict() from Items
def serialize(item):
    return item.to_dict()

#TODO move this to front end?
def items_with_same(name, description, cost, *id):
    count = 0 # Number of potential duplicates
    mapped_ids = []

    duplicate_names = Item.query.filter_by(name=name).all()
    duplicate_descs = Item.query.filter_by(description=description).all()
    all_items = duplicate_names + duplicate_descs

    duplicate_item = {}
    same_name_dict = {}
    same_description_dict = {}

    if id:
        for item in all_items:
            same_name = item.name == name
            same_cost = item.cost == cost
            same_desctiption = item.description == description
            same_item = same_name and same_cost and same_desctiption

            if not item.id == id:
                # items should be unique
                if item.id not in mapped_ids:
                    # sort query items into categories based on how they are
                    # similar to the item with itemId
                    if same_item:
                        count += 1
                        duplicate_item[count] = serialize(item)
                    elif same_name:
                        count += 1
                        same_name_dict[count] = serialize(item)
                    else:
                        count += 1
                        same_description_dict[count] = serialize(item)
                    mapped_ids.append(item.id)

    if not id:
        for item in all_items:
            same_name = item.name == name
            same_cost = item.cost == cost
            same_desctiption = item.description == description
            same_item = same_name and same_cost and same_desctiption
            if item.id not in mapped_ids:
                # sort query items into categories based on how they are
                # similar to the item with itemId
                if same_item:
                    count += 1
                    duplicate_item[count] = serialize(item)
                elif same_name:
                    count += 1
                    same_name_dict[count] = serialize(item)
                else:
                    count += 1
                    same_description_dict[count] = serialize(item)
                mapped_ids.append(item.id)


    return duplicate_item, same_name_dict, same_description_dict

    #TODO update 'PUT' found_items
    #TODO ensureif not any() still operates accurately

def serialize_found(items):
    list_of_items = []
    for key, value in items.items():
        list_of_items.append({
            'found item #' : key,
            'id': value['id'],
            'name': value['name'],
            'cost': value['cost'],
            'description': value['description']
        })
    return list_of_items

def construct_return_package(found_items):
    dup_item, dup_name_item, dup_description_item = found_items
    num_dup_item = len(dup_item)
    num_dup_name_item = len(dup_name_item)
    num_dup_description_item = len(dup_description_item)

    message = ""

    #TODO create errors[]
    # put together same named items message
    if dup_item:
        if num_dup_item > 1:
            message += "%d duplicate items" % num_dup_item
        else:
            message += "1 duplicate item"

    if dup_name_item:
        if dup_item:
            # add pluralized version of name message
            if num_dup_name_item > 1:
                message += ', %d items with the same name' % num_dup_name_item
            message += ', 1 item with the same name'
            # add singular version of name message
        message = '1 item with the same name'

    # put together same descriptioned items message
    if dup_description_item:
        # add pluralized version of description message
        if dup_item or dup_name_item:
            if num_dup_description_item > 1:
                message += ' and %d items with the same description' % num_dup_description_item
            message += ' and %d item with the same description' % num_dup_description_item
        # add singular version of description message
        else:
            message += '1 item with the same description'
    message += ' exists.'

    # message will NOT be None
    return message, dup_item, dup_name_item, dup_description_item
