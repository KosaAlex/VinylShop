function deleteProduct(productId) {
  fetch("/delete-product", {
    method: "POST",
    body: JSON.stringify({ productId: productId }),
  }).then((_res) => {
    window.location.href = "/admin";
  });
}
function updateOrder(orderId) {
  fetch("/update-order", {
    method: "POST",
    body: JSON.stringify({ orderId: orderId }),
  }).then((_res) => {
    window.location.href = "/admin";
  });
}