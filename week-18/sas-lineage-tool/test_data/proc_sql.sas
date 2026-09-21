/* PROC SQL Example
   Purpose: SQL-style data transformations
*/

PROC SQL;
    * Create summary table;
    CREATE TABLE sales_summary AS
    SELECT 
        customer_id,
        product_category,
        SUM(sales_amount) AS total_sales,
        AVG(sales_amount) AS avg_sales,
        COUNT(*) AS transaction_count,
        MAX(sale_date) AS last_purchase_date
    FROM sales_transactions
    GROUP BY customer_id, product_category
    HAVING total_sales > 1000
    ORDER BY total_sales DESC;
    
    * Join multiple tables;
    CREATE TABLE customer_product_summary AS
    SELECT 
        c.customer_id,
        c.customer_name,
        c.region,
        p.product_name,
        s.total_sales,
        s.transaction_count,
        c.lifetime_value / s.total_sales AS sales_ratio
    FROM customers AS c
    INNER JOIN sales_summary AS s
        ON c.customer_id = s.customer_id
    LEFT JOIN products AS p
        ON s.product_category = p.category;
QUIT;
