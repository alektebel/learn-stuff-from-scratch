/* Simple SAS DATA Step Example
   Purpose: Basic field transformations and lineage
*/

* Read customer data and create summary fields;
DATA customer_summary;
    SET customer_data;
    
    * Direct field copy;
    customer_id = id;
    
    * Simple calculation;
    age_years = age;
    
    * Derived field from multiple sources;
    total_revenue = price * quantity;
    
    * String manipulation;
    full_name = CATX(' ', first_name, last_name);
    
    * Conditional field;
    IF age < 18 THEN age_group = 'Youth';
    ELSE IF age < 65 THEN age_group = 'Adult';
    ELSE age_group = 'Senior';
RUN;
