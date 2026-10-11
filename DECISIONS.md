\# VIKMO DealerDesk — AI/ML Decisions



\## 1. Track



This submission targets the \*\*AI/ML track\*\*.



The implementation focuses on:



\- Dealer Assistant

\- Product and inventory retrieval

\- Draft order creation

\- Demand forecasting

\- Reorder suggestions



\---



\## 2. Dealer Assistant Architecture



The Dealer Assistant uses an LLM-based tool-calling approach.



The assistant can use backend tools instead of inventing database information.



The main tools are:



\- `search\_parts`

\- `check\_stock`

\- `create\_draft\_order`



The database is treated as the source of truth for product, inventory, dealer, and order information.



This prevents the assistant from relying only on LLM-generated information.



\---



\## 3. Product Retrieval



Product retrieval is implemented using database queries.



The search considers information such as:



\- SKU

\- Product name

\- Description

\- Vehicle fitment

\- Category

\- Brand



The assistant can therefore retrieve relevant catalogue items before responding to the dealer.



When multiple products match an ambiguous request, the assistant asks the dealer for clarification instead of selecting a product arbitrarily.



\---



\## 4. Inventory Grounding



Inventory information is retrieved from the database through the `check\_stock` tool.



The assistant does not generate stock quantities from memory.



For example, when a dealer asks for the stock of a specific SKU, the assistant queries the current inventory record and reports the result.



This keeps stock responses grounded in live application data.



\---



\## 5. Draft Order Safety



The assistant can create only \*\*DRAFT\*\* orders.



It does not directly confirm, dispatch, or deliver an order.



The draft-order workflow validates:



\- Dealer existence

\- Product existence

\- Requested quantity

\- Available stock

\- Order items



The order is created only after these validations succeed.



This was chosen as a safety measure because an AI assistant should not automatically execute an irreversible business action.



\---



\## 6. Ambiguity Handling



The assistant should not guess when a dealer request does not uniquely identify a product.



For example:



> "I need brake pads."



If several brake-pad products are available, the assistant asks for additional information such as vehicle/model or another identifying detail.



This reduces the risk of creating an incorrect order.



\---



\## 7. Prompt Injection Defense



The assistant is instructed not to reveal:



\- System prompts

\- API keys

\- Secrets

\- Internal configuration



User messages are treated as dealer requests rather than instructions that can override the assistant's application-level rules.



A prompt-injection test was performed using a request asking the assistant to reveal its system prompt and API keys. The assistant refused and continued its intended dealer-assistance role.



\---



\## 8. Forecasting Approach



The forecasting pipeline produces forecasts for:



\- 40 SKUs

\- 4 future weeks

\- 160 total forecast rows



The forecast horizon starts on:



`2026-09-28`



and contains four weekly dates.



The forecasting pipeline uses historical sales information and evaluates multiple simple forecasting approaches before selecting a model.



The generated output is stored in:



`ml/forecast.csv`



The output is validated to ensure:



\- Required columns exist

\- Exactly 160 rows are produced

\- Each SKU has four forecast weeks

\- Forecast values are non-negative



\---



\## 9. Forecasting Model Selection



Several baseline approaches are considered during forecasting, including:



\- Naive forecasting

\- Moving-average forecasting

\- Seasonal forecasting



The implementation uses historical sales data and backtesting to select an appropriate approach for each SKU.



This was preferred over using a complex deep-learning model because the assignment dataset is relatively small and the solution needs to be reproducible and explainable.



\---



\## 10. Reorder Logic



Reorder suggestions use the forecast and inventory information.



The calculation considers:



\- Current stock

\- Forecast demand

\- Supplier lead time

\- Safety stock



The reorder calculation follows the safety-stock and reorder requirements specified by the assignment.



The API exposes the resulting recommendations through:



`/api/reorder-suggestions/`



\---



\## 11. Why Database-Grounded Tools Instead of LLM-Only Answers?



An LLM alone is not reliable for exact business data such as:



\- Current inventory

\- Product SKU

\- Product price

\- Dealer information

\- Order quantities



Therefore, the LLM is used for understanding the dealer's request and deciding which tool is appropriate.



The tools then retrieve or modify application data.



This separates:



\*\*Natural-language reasoning → application tools → database truth\*\*



\---



\## 12. Why Draft Orders Instead of Automatic Confirmation?



Automatic order confirmation could create unintended business transactions.



The safer design is:



\*\*Dealer request → Assistant → validation → Draft Order\*\*



A human or authorized business workflow can then review and confirm the order.



\---



\## 13. Limitations



The current implementation is intentionally focused on the requirements of the take-home assignment.



Potential future improvements include:



\- More advanced semantic product retrieval

\- Embedding-based catalogue search

\- Better conversation memory

\- More sophisticated forecasting models

\- Forecast confidence intervals

\- Automated model monitoring

\- Role-based authorization

\- Production-grade observability

\- More extensive automated tests



\---



\## 14. Key Design Principle



The central design principle is:



> \*\*Use the LLM for language understanding and tool selection, but use the application database and deterministic business logic for business-critical facts and operations.\*\*



This reduces hallucination risk while still providing a natural-language dealer experience.

