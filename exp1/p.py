class Person:
    pass

p = Person()

# تعيين خاصية جديدة dynamically
setattr(p, 'name', 'Ali')
setattr(p, 'age', 25)
print(p.name)  # Ali
print(p.age)   # 25

# pbkdf2_sha256$600000$HTeXcLW0xXE7BjYgxzY16w$tI4tqJ0EiVd6KYRcvQdKXOasw3jv4mjTxCK1ugne/jc=
# pbkdf2_sha256$600000$H3b83oycxZNcSZIrVfipDV$p82PCPA+2p9NSMcqUINcVqC04YXAFtLdVI8685CJh9Y=



    # def update_item_quantity(self, request, pk=None, product_id=None):
    #     try:
    #         cart = self.get_object()
    #         quantity = int(request.data.get('quantity', 0))
    #         if quantity < 1:
    #             return Response({"detail": "❌ الكمية يجب أن تكون 1 أو أكثر."}, status=status.HTTP_400_BAD_REQUEST)
    #         item1 = cart.items.get(product__id=product_id)
    #         item1.quantity = quantity
    #         # item1.Sub_total = quantity * item1.product.price
    #         item1.save()
    #         # cart.grand_total = sum(i.quantity * i.product.price for i in cart.items.all())
    #         # cart.save()
    #         return Response({"detail": "✅ تم تعديل الكمية بنجاح."}, status=status.HTTP_200_OK)
    #     except CartItem.DoesNotExist:
    #         return Response({"detail": "❌ العنصر غير موجود في السلة."}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)






    # @action(detail=True, methods=['delete'], url_path='removeitem/(?P<item_id>[^/.]+)')
    # def remove_item(self, request, pk=None, item_id=None):
    #     try:
    #         cart = self.get_object()
    #         item = CartItem.objects.get(id=item_id, cart=cart)
    #         item.delete()
    #         # cart.grand_total = sum(item.Sub_total for item in cart.items.all())
    #         # cart.save()
    #         return Response({"detail": "تم حذف العنصر من السلة."}, status=status.HTTP_204_NO_CONTENT)
    #     except CartItem.DoesNotExist:
    #         return Response({"detail": "العنصر غير موجود."}, status=status.HTTP_404_NOT_FOUND)

