import os

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:7860")
REFERENCE_YEAR = 2025  # must match the reference year used to compute Store_Age_Years during training

# Product type -> (Product_Id_char, Product_Type_Category), as derived in the training data
PRODUCT_TYPES = {
    "Fruits and Vegetables": ("FD", "Perishables"), "Snack Foods": ("FD", "Non Perishables"),
    "Frozen Foods": ("FD", "Non Perishables"), "Dairy": ("FD", "Perishables"),
    "Baking Goods": ("FD", "Non Perishables"), "Canned": ("FD", "Non Perishables"),
    "Meat": ("FD", "Perishables"), "Breads": ("FD", "Perishables"),
    "Starchy Foods": ("FD", "Non Perishables"), "Breakfast": ("FD", "Perishables"),
    "Seafood": ("FD", "Perishables"), "Soft Drinks": ("DR", "Non Perishables"),
    "Hard Drinks": ("DR", "Non Perishables"), "Household": ("NC", "Non Perishables"),
    "Health and Hygiene": ("NC", "Non Perishables"), "Others": ("NC", "Non Perishables"),
}
REQUIRED_COLUMNS = [
    "Product_Weight", "Product_Sugar_Content", "Product_Allocated_Area", "Product_MRP", "Store_Size",
    "Store_Location_City_Type", "Store_Type", "Product_Id_char", "Store_Age_Years", "Product_Type_Category",
]

st.set_page_config(page_title="SuperKart Sales Forecaster", layout="centered")
st.title("SuperKart Sales Forecaster")
st.caption("Forecasts the total revenue a product will generate in a store (Product_Store_Sales_Total).")

single_tab, batch_tab = st.tabs(["Single product", "Batch (CSV upload)"])

with single_tab:
    with st.form("single_prediction"):
        st.subheader("Product")
        p1, p2 = st.columns(2)
        product_type = p1.selectbox("Product type", list(PRODUCT_TYPES), index=1)
        sugar_content = p2.selectbox("Sugar content", ["Low Sugar", "Regular", "No Sugar"])
        product_weight = p1.number_input("Product weight", min_value=1.0, max_value=40.0, value=12.66, step=0.1)
        product_mrp = p2.number_input("Product MRP", min_value=1.0, max_value=1000.0, value=117.08, step=0.5)
        allocated_area = p1.number_input("Allocated display area (share of store display)", min_value=0.0,
                                         max_value=1.0, value=0.027, step=0.001, format="%.3f")

        st.subheader("Store")
        s1, s2 = st.columns(2)
        store_type = s1.selectbox("Store type", ["Supermarket Type2", "Supermarket Type1", "Departmental Store",
                                                 "Food Mart"])
        store_size = s2.selectbox("Store size", ["Medium", "High", "Small"])
        city_type = s1.selectbox("City tier", ["Tier 2", "Tier 1", "Tier 3"])
        established = s2.number_input("Store establishment year", min_value=1950, max_value=REFERENCE_YEAR,
                                      value=2009, step=1)
        submitted = st.form_submit_button("Predict sales", type="primary")

    if submitted:
        id_char, type_category = PRODUCT_TYPES[product_type]
        if id_char == "NC" and sugar_content != "No Sugar":
            st.info("Non-consumable products are always recorded as 'No Sugar'; the sugar content was adjusted.")
            sugar_content = "No Sugar"

        payload = {
            "Product_Weight": product_weight,
            "Product_Sugar_Content": sugar_content,
            "Product_Allocated_Area": allocated_area,
            "Product_MRP": product_mrp,
            "Store_Size": store_size,
            "Store_Location_City_Type": city_type,
            "Store_Type": store_type,
            "Product_Id_char": id_char,
            "Store_Age_Years": int(REFERENCE_YEAR - established),
            "Product_Type_Category": type_category,
        }
        try:
            response = requests.post(f"{BACKEND_URL}/v1/predict", json=payload, timeout=30)
            response.raise_for_status()
            predicted = response.json()["Predicted_Sales"]
            st.metric("Predicted Product_Store_Sales_Total", f"{predicted:,.2f}")
        except requests.RequestException as exc:
            st.error(f"The prediction service could not be reached or returned an error: {exc}")
        with st.expander("Features sent to the API"):
            st.json(payload)

with batch_tab:
    st.write("Upload a CSV file with these columns: " + ", ".join(f"`{c}`" for c in REQUIRED_COLUMNS))
    uploaded = st.file_uploader("CSV file", type=["csv"])
    if uploaded is not None:
        batch_df = pd.read_csv(uploaded)
        st.write(f"{len(batch_df):,} rows loaded")
        st.dataframe(batch_df.head(), use_container_width=True)
        missing = [c for c in REQUIRED_COLUMNS if c not in batch_df.columns]
        if missing:
            st.error(f"Missing column(s): {missing}")
        elif st.button("Predict for all rows", type="primary"):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/v1/predictbatch",
                    files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
                    timeout=120,
                )
                response.raise_for_status()
                predictions = response.json()
                result = batch_df.copy()
                result["Predicted_Sales"] = [predictions[str(i)] for i in range(len(result))]
                st.success("Predictions completed.")
                st.metric("Total predicted sales", f"{result['Predicted_Sales'].sum():,.2f}")
                st.dataframe(result, use_container_width=True)
                st.download_button("Download predictions", result.to_csv(index=False).encode("utf-8"),
                                   file_name="superkart_predictions.csv", mime="text/csv")
            except requests.RequestException as exc:
                st.error(f"The prediction service could not be reached or returned an error: {exc}")
