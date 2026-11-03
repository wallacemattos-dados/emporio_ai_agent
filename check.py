import duckdb
print(duckdb.sql("select count(*) from 'data/products.csv'"))
