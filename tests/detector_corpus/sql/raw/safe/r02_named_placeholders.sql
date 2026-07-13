SELECT id, status, total FROM orders WHERE customer_id = :customer_id AND status = :status ORDER BY created_at DESC;
