from flask import Blueprint, request, g, jsonify, abort
from datetime import datetime

from app import app, db

from app.auth.decorators import requires_login, requires_admin, requires_at_least_server
from app.auth.models.User import User
from app.auth import constants as USER

from app.bill.models.Bill import Bill
from app.bill.validators.BillValidator import BillValidator

from app.item.models.Item import Item

from app.restaurant.models.Restaurant import Restaurant

from app.core.helpers import success, error


billMod = Blueprint('bills', __name__, url_prefix='/bills')


@billMod.route('/')
@requires_login
@requires_admin
def bill_index():
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

    bill_query = None

    bill_query = Bill.query.paginate(page,25,False)

    bills = []

    for b in bill_query.items:
        bill = b.to_dict()
        print(bill)

        bills.append(bill)

    return jsonify({
        'status' : 'success',
        'meta' : {
            'page' : bill_query.page,
            'pages' : bill_query.pages,
            'total' : bill_query.total
        },
        'data' : {
            'bills' : bills
        }
    })


@billMod.route('/restaurant/<int:restaurantId>', methods=['GET', 'POST'])
@requires_login
@requires_at_least_server
def restaurant_bill_index(restaurantId):
    restaurant = Restaurant.query.filter(Restaurant.id==restaurantId).all()

    if not restaurant:
        return jsonify(error('Unable to find restaurant', {
            'restaurant_id' : ['No restaurant with id of %d' % restaurantId]
        })), 404

    restaurant = restaurant[0]


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

        bill_query = Bill.query.filter(Bill.restaurant_id==restaurantId).paginate(page, 25, False)

        bills = []

        for b in bill_query.items:
            bill = b.to_dict()
            bill['customer'] = b.customer.to_dict()

            items = []
            for item in b.items:
                items.append(item.to_dict())

            bill['items'] = items
            bills.append(bill)

        return jsonify({
            'status' : 'success',
            'meta' : {
                'page' : bill_query.page,
                'pages' : bill_query.pages,
                'total' : bill_query.total
            },
            'data' : {
                'bills' : bills
            }
        })

    else:
        try:
            request.json['customer_id'] = int(request.json['customer_id'])
        except:
            return jsonify(error('There was a problem with the request',{
                'customer_id' : ['Customer id must be an integer > 0']
            })), 400


        form = BillValidator(data=request.json)

        if form.validate():
            customer = User.query.filter(User.id==request.json['customer_id']).all()

            if not customer:
                return jsonify(error('Unable to find user', {
                    'customer_id' : ['Unable to find user with id of %d' % request.json['customer_id']]
                })), 400

            customer = customer[0]

            items = []

            if 'items' in request.json:
                for i, item_id in enumerate(request.json['items']):
                    ## check if item exists
                    try:
                        item_id = int(item_id)
                        if item_id < 0:
                            raise Exception('Not integer for item id')
                    except:
                        return jsonify(error('Item id must be a positive integer', {
                            'items' : {
                                i: 'Item id must be a positive integer.'
                            }
                        })), 400


                    item = Item.query.find.all(Item.id==item_id)

                    if not item:
                        return jsonify('Unable to find item', {
                            'items' : {
                                i : 'Item not found'
                            }
                        }), 400

                    items.append(item)

            json = request.json

            if not 'created_at' in json:
                json['created_at'] = datetime.now()

            bill = Bill(customer, json['paid'], json['reciept_number'], json['message'], json['created_at'])

            bill.items = items
            bill.restaurant_id = restaurantId

            try:
                db.session.add(bill)
                db.session.commit()
            except:
                return jsonify(error('There was a problem', {
                    'server' : 'There was a server error'
                })), 500


            data = {
                'bill' : bill.to_dict(),
            }


            if items:
                itemJson = []
                for item in items:
                    itemJson.append(item.to_dict())

                data['items'] = itemJson



            return jsonify(success('Bill created', data)), 201


        return jsonify(error('There was a problem with the request', form.errors)), 400

@billMod.route('/<int:billId>', methods=['GET', 'PUT', 'DELETE'])
@requires_login
def bill_single(billId):
    bills = None

    try:
        bills = Bill.query.filter(Bill.id==billId).all()
    except:
        return(error('Unable to find Bill.', {
            'bill' : ['Unable to find bill']
        })), 400

    if not bills:
        return(error('Unable to find Bill.', {
            'bill' : ['Unable to find bill']
        })), 400

    bill = bills[0]


    is_customer = bill.customer.id is g.user.id
    is_at_least_server = g.user.role >= USER.SERVER # check is right restaurant

    if not is_customer and not is_at_least_server:
        abort(403)
    elif is_at_least_server and not is_customer:
        if not hasattr(g.user, 'restaurant'):
            abort(403)

        if g.user.restaurant != bill.restaurant_id:
            abort(403)


    if request.method == 'GET':
        # check if user owns bill
        data = {}
        data['bill'] = bill.to_dict()

        items = []

        for item in bill.items:
            items.append(item.to_dict())
        print(data)
        data['items'] = items
        data['bill']['customer_id'] = bill.customer_id

        return jsonify(success('Bill found', data))
