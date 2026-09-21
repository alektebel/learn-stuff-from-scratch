/* Complex SAS Transformations
   Purpose: Multiple datasets, merges, and complex logic
*/

* Merge customer and transaction data;
DATA customer_transactions;
    MERGE customers (IN=a) 
          transactions (IN=b);
    BY customer_id;
    
    IF a AND b;  /* Inner join */
    
    * Calculate metrics from multiple sources;
    avg_transaction = total_amount / transaction_count;
    
    * Complex conditional logic;
    IF segment = 'Premium' AND total_amount > 1000 THEN DO;
        discount_rate = 0.15;
        loyalty_points = total_amount * 2;
    END;
    ELSE IF segment = 'Standard' THEN DO;
        discount_rate = 0.05;
        loyalty_points = total_amount;
    END;
    
    * Date calculations;
    days_since_signup = TODAY() - signup_date;
    
    * Array processing;
    ARRAY monthly{12} jan feb mar apr may jun jul aug sep oct nov dec;
    DO i = 1 TO 12;
        monthly{i} = monthly{i} * 1.1;  /* 10% increase */
    END;
    
    * Keep only needed fields;
    KEEP customer_id avg_transaction discount_rate loyalty_points;
RUN;
