/* Multiple Dataset Lineage
   Purpose: Track lineage across multiple data steps
*/

* Step 1: Read raw data and clean;
DATA cleaned_customers;
    SET raw_customers;
    
    * Clean and standardize fields;
    clean_name = UPCASE(TRIM(customer_name));
    clean_email = LOWCASE(TRIM(email));
    
    * Derive new fields;
    signup_year = YEAR(signup_date);
    age_at_signup = signup_year - birth_year;
RUN;

* Step 2: Calculate customer segments;
DATA customer_segments;
    SET cleaned_customers;
    
    * Segment based on multiple criteria;
    IF age_at_signup < 25 THEN segment = 'Young';
    ELSE IF age_at_signup < 50 THEN segment = 'Middle';
    ELSE segment = 'Mature';
    
    * Add value tier;
    IF total_purchases > 10000 THEN value_tier = 'High';
    ELSE IF total_purchases > 1000 THEN value_tier = 'Medium';
    ELSE value_tier = 'Low';
RUN;

* Step 3: Create final output;
DATA final_customer_report;
    SET customer_segments;
    
    * Combine segment and tier;
    customer_category = CATX('-', segment, value_tier);
    
    * Calculate derived metrics;
    avg_purchase = total_purchases / purchase_count;
    
    * Final fields to keep;
    KEEP customer_id clean_name clean_email customer_category avg_purchase;
RUN;
