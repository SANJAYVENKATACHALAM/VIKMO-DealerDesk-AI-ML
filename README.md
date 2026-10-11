\# VIKMO DealerDesk — AI/ML Track



DealerDesk is a Django REST API for automotive dealers to search products, check inventory, create draft orders, interact with an AI Dealer Assistant, and receive demand forecasts and reorder suggestions.



This submission targets the \*\*AI/ML track\*\*.



\## Features



\### Core Backend

\- Product catalogue API

\- Product detail API

\- Dealer management

\- Inventory management

\- Draft order creation

\- PostgreSQL database

\- Idempotent seed data



\### Dealer Assistant

\- Natural-language dealer queries

\- Product search

\- Live inventory lookup

\- Draft order creation

\- Ambiguous product clarification

\- Database-grounded responses

\- Prompt-injection protection

\- Session-based conversation context



Assistant tools:



\- `search\_parts`

\- `check\_stock`

\- `create\_draft\_order`



\### Forecasting

\- Forecasts for 40 SKUs

\- Four future weekly periods

\- 160 forecast rows

\- Historical sales-based forecasting

\- Model selection using backtesting

\- Reorder suggestions

\- Safety-stock based reorder calculation



\## Technology Stack



\- Python 3.11+

\- Django

\- Django REST Framework

\- PostgreSQL

\- Pandas

\- Requests

\- LLM-based tool calling

\- SQL/database-grounded retrieval



\## Project Structure



```text

.

├── core/

│   ├── assistant.py

│   ├── models.py

│   ├── views.py

│   ├── urls.py

│   └── management/

├── data/

│   ├── catalogue.csv

│   ├── dealers.csv

│   ├── sales\_history.csv

│   ├── lead\_times.csv

│   ├── promo\_calendar.csv

│   └── festival\_calendar.csv

├── dealerdesk/

├── ml/

│   ├── build\_forecast.py

│   └── forecast.csv

├── supplier\_mock/

├── manage.py

├── requirements.txt

├── smoke\_test.py

├── DECISIONS.md

└── README.md

