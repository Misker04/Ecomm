# Online Marketplace (PA1) - TCP Socket Implementation

This project implements an online marketplace using 6 components: Buyer CLI, Seller CLI, Buyer Frontend Server, Seller Frontend Server, Customer DB Service, and Product DB Service. All interprocess communication uses raw TCP sockets with a 4-byte length-prefixed JSON protocol. Frontend servers are stateless and store no persistent user/session/cart/item state; all persistent state is stored in the backend database services. Login returns a session_id which must be included in all subsequent authenticated requests. Session timeout is enforced in Customer DB: sessions expire after 300 seconds of inactivity. Shopping carts are stored in Product DB and are cleared on logout unless SaveCart was invoked. MakePurchase is not implemented (per assignment); GetBuyerPurchases returns an empty list with a note. Search semantics: category must match and items must have quantity>0; score is number of exact case-insensitive keyword matches; results sorted by score desc, net feedback desc, price asc, item_id asc. Current state: all seller and buyer APIs (except MakePurchase) are supported; persistence is via JSON snapshot files in /data.


python -m src.customer_db.server --config config/local.yaml
python -m src.product_db.server --config config/local.yaml
python -m src.frontend_buyer.server --config config/local.yaml
python -m src.frontend_seller.server --config config/local.yaml

Remove-Item .\data\*.tmp -ErrorAction SilentlyContinue

python -m src.clients.bench.runner --config config/local.yaml --scenario 1
