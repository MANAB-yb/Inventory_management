from django.urls import path
from manage_inventory.controllers.product_controller import ProductController, SupplierController, StockMovementController, SaleOrderController
from . import views

urlpatterns = [
    # endpoint to fetch/ add products in the inventory
    path('products', ProductController.as_view(), name="list_all_products"),
    # endpoint to fetch all the 
    path('suppliers', SupplierController.as_view(), name="list_and_post_suppliers"),
    # update stock of a product
    path('stock_movement', StockMovementController.as_view(), name="update_stock_of_a_product"),
    # sale order controller
    path('sale_order', SaleOrderController.as_view(), name="create_and_update_sale_order")
]
