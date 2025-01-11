import json
import re
from datetime import datetime
from bson import ObjectId
from manage_inventory.models import Product, Sale_order, Stock_Movement
from rest_framework.views import APIView
from rest_framework.response import Response
from manage_inventory.models import Supplier
from rest_framework import status
from django.http import HttpResponse, JsonResponse
import traceback
from django.db import transaction

class ProductController(APIView):
    model = Product

    def get(self, request, _id=None):
        """
        list of all products in the inventory
        """
        try:
            product_list = list(self.model.find())
            for product in product_list:
                product['_id'] = str(product['_id'])
                # get the respective supplier
                supplier_id = product['supplier']
                product.pop('supplier')
                supplier = Supplier.find_one({"_id": supplier_id})
                # print(supplier)
                if not supplier:
                    return HttpResponse("Error: found products without supplier", status=500)
                product['supplier_name'] = supplier['name']
                product['supplier_email'] = supplier['email']
            return JsonResponse(product_list, safe=False)
        except Exception as ex:
            print(f"error caused during the process {ex}")
            return HttpResponse(f"Error: {ex}", status=500)
    
    def post(self, request):
        """
        Add product into the inventory
        """
        # validating if the product already exist in the DB using product name, category and supplier
        try:
            prod_name = request.data.get("name")
            description = request.data.get("description")
            category = request.data.get("category")
            price = float(request.data.get("price"))
            stock_quantity = int(request.data.get("stock_quantity"))
            supplier_id = request.data.get("supplier_id")
            supplier_id = ObjectId(supplier_id)

            similar_product = Product.find_one({"name": prod_name,
                                                "category": category,
                                                "supplier": supplier_id})
            
            if similar_product:
                print(f"aborting adding similar record for product {prod_name}")
                return HttpResponse(f"Error: Similar product exists, with id {str(similar_product['_id'])}", status=403)
            else:
                # insert the record
                # validate such supplier exists
                supplier = Supplier.find_one({"_id": supplier_id})
                if not supplier:
                    return HttpResponse(f"Error: no such supplier exists", status=403)
                product = {
                    "name": prod_name,
                    "description": description,
                    "category": category,
                    "price": price,
                    "stock_quantity": stock_quantity,
                    "supplier": supplier_id
                }
                Product.insert_one(product)
                return HttpResponse(f"successfully added the product to our database !!", status=200)
        except Exception as ex:
            print(f"error caused in post call to post the product, {ex}")
            return HttpResponse(f"Error: {ex}", status=500)
        

class SupplierController(APIView):
    
    def get(self, request, _id=None):
        """
        list all the suppliers
        """
        try:
            supplier_list = list(Supplier.find())
            for supplier in supplier_list:
                supplier['_id'] = str(supplier['_id'])

            return JsonResponse(supplier_list, safe=False)
        except Exception as ex:
            print(f"list all suppliers failed due to {ex}")
            return HttpResponse(f"error: {ex}", status=500)
        
    def post(self, request):
        """
        post a new supplier
        """
        try:
            name = request.data.get("name")
            email = request.data.get("email")
            phone = request.data.get("phone")
            address = request.data.get("address")

            same_supplier = Supplier.find_one({
                "name": name,
                "email": email,
                "phone": phone,
                "address": address
            })
            
            if same_supplier:
                print(f"Abborting post supplier as {str(same_supplier['_id'])} already exists")
                return HttpResponse(f"Record for this supplier {str(same_supplier['_id'])} exists", status=403)
            
            supplier = {
                "name": name,
                "email": email,
                "phone": phone,
                "address": address
            }
            Supplier.insert_one(supplier)
            return HttpResponse(f"successfully added the supplier to our database !!", status=200)
        except Exception as ex:
            print(f'post new supplier failed due to {ex}')
            return HttpResponse(f"Error: {ex}", status=500)

class StockMovementController(APIView):
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            product_id = ObjectId(product_id)
            # check if the product is available in the DB
            target_product = Product.find_one({'_id': product_id})
            if not target_product:
                return HttpResponse(f"No such product available", status=403)
            quantity = int(request.data.get('quantity'))
            movement_type = request.data.get('movement_type')
            # validate Movement type
            if str(movement_type).lower() not in ["in", "out"]:
                return HttpResponse(f"unknown movement type, movement type should be in [In, Out]", status=403)
            movement_date = str(request.data.get('movement_date')) # expected date in type "%Y-%m-%d"
            date_pattern = r"^\d{4}-\d{2}-\d{2}$"
            if not re.match(date_pattern, movement_date):
                return HttpResponse(f"unknown date pattern, expected pattern for date is ^\d{4}-\d{2}-\d{2}$", status=403)
            movement_date = datetime.strptime(movement_date, "%Y-%m-%d")
            notes = request.data.get('notes')

            
            # fetch the product
            product = Product.find_one({'_id': product_id})
            print(product)
            existing_quantity = int(product['stock_quantity'])
            quantty_to_add = quantity if str(movement_type).lower() == 'in' else -1 * quantity
            if existing_quantity + quantty_to_add < 0:
                return HttpResponse(f"{quantity} items is not present in the DB for product {product_id}", status=403)
            
            # update the product
            product['stock_quantity'] = existing_quantity + quantty_to_add
            # with transaction.atomic():
            result = Product.update_one({"_id": ObjectId(product_id)}, {"$set": product})
            if result.matched_count > 0:
                stock_movement = {
                    "product": ObjectId(product_id),
                    "quantity": quantity,
                    "movement_type": movement_type,
                    "movement_date": movement_date,
                    "notes": notes
                }
                Stock_Movement.insert_one(stock_movement)
                return HttpResponse("Successfully Updated product quantity to to DB", status=200)
            else:
                return HttpResponse("no products found in DB", status=200)
        except Exception as ex:
            print(f"failed to update stock movement, due to {ex} {traceback.format_exc()}")
            return HttpResponse(f"error: {ex}", status=500)

class MockRequest:
    def __init__(self, data):
        self.data = data

class SaleOrderController(APIView):
    def get(self, request, _id=None):
        """
        list all the sale orders
        """
        try:
            sale_orders = list(Sale_order.find())
            for sale_order in sale_orders:
                product_id = ObjectId(sale_order['product'])
                product = Product.find_one({'_id': product_id})
                product_name = product['name']
                sale_order['product_name'] = str(product_name)
                for key in sale_order:
                    sale_order[key] = str(sale_order[key])

            return JsonResponse(sale_orders, safe=False)
        except Exception as ex:
            print(f"failed to list the order due to {ex}")
            return HttpResponse(f"error: {ex}", status=500)

    def post(self, request):
        """
        Create a new Sale Order
        """
        try:
            product_id = request.data.get('product_id')
            product_id = ObjectId(product_id)
            quantity = int(request.data.get('quantity'))
            status = "Pending"
            # try to fetch the product
            product = Product.find_one({'_id': product_id})
            print(product)
            if not product:
                return HttpResponse(f"no such product available", status=403)
            product_name = product['name']
            unit_price = float(product['price'])
            total_price = unit_price * quantity
            current_stock = int(product['stock_quantity'])
            if current_stock < quantity:
                return HttpResponse("we don't have sufficient stock", status=403)
            
            # Sale_order
            sale_order = {
                "product": product_id,
                "quantity": quantity,
                "total_price": total_price,
                "sale_date": None, # it's not yet sold
                "status": "Pending"
            }

            # update the product's stock
            product['stock_quantity'] = current_stock - quantity
            result = Product.update_one({"_id": ObjectId(product_id)}, {"$set": product})

            # update sale order
            Sale_order.insert_one(sale_order)
            for key in sale_order:
                sale_order[key] = str(sale_order[key])
            sale_order['product_name'] = product_name
            return JsonResponse(sale_order, safe=False)

        except Exception as ex:
            print(f"Create new Sale order failed due to {ex}")
            return HttpResponse(f"error: {ex}", status=500)


    def put(self, request, _id=None):
        """
        update/ complete a sale Order
        """
        try:
            sale_order_id = request.data.get('sale_order')
            sale_order_id = ObjectId(sale_order_id)
            sale_order = Sale_order.find_one({'_id': sale_order_id})
            if not sale_order:
                return HttpResponse("No such Sale order found", status=403)
            # update the selling date in the sale order and complete the order
            # with transaction.atomic():
            today_date = datetime.now().strftime("%Y-%m-%d")
            # update datetime in saleorder and status
            updated_field = {
                "sale_date": today_date,                    
                "status": "Completed"
            }
            Sale_order.update_one({'_id': sale_order_id}, {"$set": updated_field})

                # create Stock Movement
            stock_movement_entry = {
                "product_id": ObjectId(sale_order['product']),
                "quantity": sale_order['quantity'],
                "movement_type": "Out",
                "movement_date": today_date,
                "notes": f"update for sale order {str(sale_order_id)}"
            }
            Stock_Movement.insert_one(stock_movement_entry)
            return HttpResponse("Successfully updated the DB", status=200)

        except Exception as ex:
            print(f"failed to sell the order due to {ex}")
            return HttpResponse(f"error: {ex}", status=500)
    def delete(self, request, _id=None):
        """
        delete/ cancel a sale order
        """
        try:
            sale_order_id = request.data.get('sale_order_id')
            sale_order_id = ObjectId(sale_order_id)
            sale_order = Sale_order.find_one({'_id': sale_order_id})
            if not sale_order:
                return HttpResponse("No such Sale order found", status=403)
            
            today_date = datetime.now().strftime("%Y-%m-%d")
            # update datetime in saleorder and status
            updated_field = {
                "sale_date": today_date,                    
                "status": "Cancelled"
            }
            Sale_order.update_one({'_id': sale_order_id}, {"$set": updated_field})

            product_id = ObjectId(sale_order['product'])
            product = Product.find_one({'_id': product_id})

            if not product:
                return HttpResponse("No such Product found, mentioned in the sale order", status=403)
            
            # update the quantity in product
            quatity_to_add = sale_order['quantity']
            product['stock_quantity'] += int(quatity_to_add)

            Product.update_one({'_id': product_id}, {"$set": product})

            return HttpResponse("Successfully cancelled Sale order", status=200)

        except Exception as ex:
            print(f"failed to cancel the order due to {ex}")
            return HttpResponse(f"error: {ex}", status=500)