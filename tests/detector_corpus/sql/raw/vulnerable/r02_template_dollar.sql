SELECT id, status, total FROM orders WHERE customer_id = ${customerId} AND status = 'open';
